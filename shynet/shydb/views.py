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
        command = data.get('type')
        if command not in self.COMMANDS:
            raise BadRequest('Invalid command')

        response = getattr(self, f'_{command}')(db, data)

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

    def _get(self, db, command):
        if 'field' in command:
            return self._get_field(db, command)
        elif 'fields' in command:
            return {self._get_field(db, field) for field in command['fields']}

        return {'response': db.value}

    def _get_field(self, db, field):
        name = field.get('field')
        if isinstance(db.value[name], list) and 'where' in field:
            filter_func = self._get_filter_func(field['where'])

            return {name: [value for value in filter(filter_func, db.value[name])]}

        return {name: db.value.get(name)}

    def _set(self, db, command):
        self._validate_mutable_command(db, command)

        db.value[command['field']] = command.get('value')
        db.save()

        return {'response': 'ok'}

    def _add(self, db, command):
        self._validate_mutable_command(db, command)

        field = command['field']
        value = command.get('value')
        if isinstance(db.value[field], list):
            db.value[field].append(value)
        else:
            db.value[field] = value

        db.save()

        return {'response': 'ok'}

    def _remove(self, db, command):
        self._validate_mutable_command(db, command)

        if command['field'] not in db.value:
            return {'response': 'ok'}

        field = command['field']
        if isinstance(db.value[field], list) and 'where' in command:
            filter_func = self._get_filter_func(command['where'])
            for item in filter(filter_func, db.value[field]):
                db.value[field].remove(item)
        else:
            del db.value[command['field']]

        db.save()

        return {'response': 'ok'}

    def _get_filter_func(self, where):
        where_field = where.get('field')
        where_type = where.get('type')
        where_value = self._convert_where_value(where.get('value'), where_type)
        operator = where.get('operator', '=')

        def filter_func(item):
            if isinstance(item, dict):
                item = item.get(where_field)
                if not item:
                    return False

            try:
                match operator:
                    case '=':
                        return item == where_value
                    case '>':
                        return item > where_value
                    case '>=':
                        return item >= where_value
                    case '<':
                        return item < where_value
                    case '<=':
                        return item <= where_value
            except TypeError:
                raise BadRequest('Invalid where value type')

            return False

        return filter_func

    def _convert_where_value(self, where_value, where_type):
        if where_type not in ('int', 'float'):
            return where_value

        try:
            if where_type == 'int':
                return int(where_value)
            elif where_value == 'float':
                return float(where_value)
        except ValueError:
            raise BadRequest('Where value does not match where type')

    def _validate_mutable_command(self, db, command):
        if not db.api_editable:
            raise BadRequest('DB is not api editable')
        if 'field' not in command:
            raise BadRequest('No field specified')
