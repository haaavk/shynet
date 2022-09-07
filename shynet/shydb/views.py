import json

from django.http import JsonResponse, Http404
from django.core.exceptions import BadRequest
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


from api.mixins import ApiTokenRequiredMixin
from .models import ShyDB


@method_decorator(csrf_exempt, name='dispatch')
class ShyDBApiView(ApiTokenRequiredMixin, View):
    COMMANDS = ('set', 'get', 'add', 'remove')

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Http404:
            return JsonResponse(status=404)
        except BadRequest as e:
            return JsonResponse(status=400, data={'error': e.args[0]})
        except Exception as e:
            return JsonResponse(status=500, data={'error': e.args[0]})

    def post(self, request, *args, **kwargs):
        data = self._parse_json(request.body)
        db = self._get_db(data)
        if 'commands' in data:
            commands = enumerate(data['commands'])
            response = {idx: self.perform(db, cmd) for idx, cmd in commands}
        else:
            response = self.perform(db, data)

        return JsonResponse(data=response)

    def _parse_json(self, body):
        if len(body) == 0:
            return {}

        try:
            data = json.loads(body)
        except Exception:
            raise BadRequest('Invalid json')

        return data

    def _get_db(self, data):
        if 'db' not in data:
            raise BadRequest('No db key')

        db = ShyDB.objects.filter(key=data['db']).first()

        if db is None:
            raise Http404

        return db

    def perform(self, db, command):
        command_type = command.get('type')
        if command_type not in self.COMMANDS:
            return {'response': 'error', 'details': 'Invalid command'}

        return getattr(self, f'_{command_type}')(db, command)

    def _get(self, db, command):
        if 'name' in command:
            return self._get_field(db, command)
        elif 'fields' in command:
            return {self._get_field(db, field) for field in command['fields']}

        return {'response': db.value}

    def _get_field(self, db, field):
        name = field.get('name')
        if isinstance(db.value[name], list) and 'where' in field:
            filter_func = self._get_filter_func(field['where'])

            return {
                field['name']: value for value in filter(filter_func, db.value[name])
            }

        return {field['name']: db.value.get(field['name'])}

    def _set(self, db, command):
        if not db.api_editable:
            return {'response': 'error', 'detils': 'DB is not api editable'}
        if 'field' not in command:
            return {'response': 'error', 'detils': 'No field specified'}

        db.value[command['field']] = command.get('value')
        db.save()

        return {'response': 'ok'}

    def _add(self, db, command):
        if not db.api_editable:
            return {'response': 'error', 'detils': 'DB is not api editable'}
        if 'field' not in command:
            return {'response': 'error', 'detils': 'No field specified'}

        field = command['field']
        value = command.get('value')
        if isinstance(db.value[field], list):
            db.value[field].append(value)
        else:
            db.value[field] = value

        db.save()

        return {'response': 'ok'}

    def _remove(self, db, command):
        if not db.api_editable:
            return {'response': 'error', 'detils': 'DB is not api editable'}
        if 'field' not in command:
            return {'response': 'error', 'detils': 'No field specified'}

        if command['field'] not in db.value:
            return {'response': 'ok'}

        field = command['field']
        if isinstance(db.value[field], list) and 'where' in command:
            where_field = command['where'].get('field')
            where_value = command['where'].get('value')
            for item in db.value[field]:
                if isinstance(item, dict) and item.get(where_field) == where_value:
                    db.value[field].remove(item)
                elif item == where_value:
                    db.value[field].remove(item)
        else:
            del db.value[command['field']]

        db.save()

        return {'response': 'ok'}
