import json

from django.db import transaction
from django.http import JsonResponse, Http404
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError


from api.mixins import ApiTokenRequiredMixin
from .models import ShyDB


class ApiException(Exception):
    data = {}

    def __init__(self, error):
        self.data["error"] = error


@method_decorator(csrf_exempt, name="dispatch")
class ShyDBApiView(ApiTokenRequiredMixin, View):
    COMMANDS = ("set", "get", "add", "remove")

    def dispatch(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                response = super().dispatch(request, *args, **kwargs)
        except Http404:
            response = JsonResponse(status=404)
        except ApiException as e:
            response = JsonResponse(status=400, data=e.data)

        return response

    def post(self, request, *args, **kwargs):
        data = self._parse_json(request.body)
        db = self._get_db(data)
        if "commands" in data:
            response = {}
            for idx, cmd in enumerate(data["commands"]):
                try:
                    response[idx] = self.perform(db, cmd)
                except ApiException as e:
                    e.data = {idx: e.data}
                    raise e
        else:
            response = self.perform(db, data)

        return JsonResponse(data=response)

    def _parse_json(self, body):
        if len(body) == 0:
            return {}

        try:
            data = json.loads(body)
        except Exception:
            raise ApiException()

        return data

    def _get_db(self, data):
        if "db" not in data:
            raise ApiException("No db key")

        db = ShyDB.objects.filter(key=data["db"]).first()

        if db is None:
            raise Http404

        return db

    def perform(self, db, command):
        command_type = command.get("type")
        if command_type not in self.COMMANDS:
            raise ApiException({"error": "Invalid command"})

        return getattr(self, f"_{command_type}")(db, command)

    def _get(self, db, command):
        if "field" in command:
            name, value = self._get_field(db, command)
            return {name: value}
        elif "fields" in command:
            fields = [self._get_field(db, field) for field in command["fields"]]
            return {name: value for (name, value) in fields}

        return {"response": db.value}

    def _get_field(self, db, field):
        name = None
        if isinstance(field, str):
            name = field
        if isinstance(field, dict):
            name = field.get("field")
            if isinstance(db.value.get(name), list) and "where" in field:
                filter_func = self._get_filter_func(field["where"])

                return name, [value for value in filter(filter_func, db.value[name])]

        return name, db.value.get(name)

    def _set(self, db, command):
        self._validate_mutable_command(db, command)

        field = command["field"]
        if isinstance(db.value[field], list) and "where" in command:
            filter_func = self._get_filter_func(command["where"])
            index, _ = self._get_first_maching(db.value[field], filter_func)
            if index:
                db.value[field][index] = command.get("value")
        else:
            db.value[field] = command.get("value")

        try:
            db.save()
        except ValidationError as e:
            raise ApiException(e.messages)

        return {"response": "ok"}

    def _add(self, db, command):
        self._validate_mutable_command(db, command)

        field = command["field"]
        value = command.get("value")
        max_length = command.get("max_length")
        if not isinstance(db.value[field], list):
            raise ApiException({"error": "Field is not a list"})

        db.value[field].append(value)

        if isinstance(max_length, int):
            while len(db.value[field]) > max_length:
                db.value[field].pop(0)

        try:
            db.save()
        except ValidationError as e:
            raise ApiException(e.messages)

        return {"response": "ok"}

    def _remove(self, db, command):
        self._validate_mutable_command(db, command)

        if command["field"] not in db.value:
            return {"response": "ok"}

        field = command["field"]
        if isinstance(db.value[field], list) and "where" in command:
            filter_func = self._get_filter_func(command["where"])
            for item in filter(filter_func, db.value[field]):
                db.value[field].remove(item)
        else:
            del db.value[command["field"]]

        db.save()

        return {"response": "ok"}

    def _get_filter_func(self, where):
        where_field = where.get("field")
        where_type = where.get("type")
        where_value = self._convert_where_value(where.get("value"), where_type)
        operator = where.get("operator", "=")

        def filter_func(item):
            if isinstance(item, dict):
                field = item.get(where_field)
                if not field:
                    return False

            try:
                match operator:
                    case "=":
                        return field == where_value
                    case ">":
                        return field > where_value
                    case ">=":
                        return field >= where_value
                    case "<":
                        return field < where_value
                    case "<=":
                        return field <= where_value
            except TypeError:
                raise ApiException("Invalid where value type")

            return False

        return filter_func

    def _get_first_maching(self, collection, filter_func):
        for index, item in enumerate(collection):
            if filter_func(item):
                return index, item

        return None, None

    def _convert_where_value(self, where_value, where_type):
        if where_type not in ("int", "float"):
            return where_value

        try:
            if where_type == "int":
                return int(where_value)
            elif where_value == "float":
                return float(where_value)
        except ValueError:
            raise ApiException("Where value does not match where type")

    def _validate_mutable_command(self, db, command):
        if not db.api_editable:
            raise ApiException("DB is not api editable")
        if "field" not in command:
            raise ApiException("No field specified")
