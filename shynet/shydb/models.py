from django.db import models
from core.models import User, _default_uuid
from django.core.exceptions import ValidationError


from jsonschema import Draft202012Validator as Validator


class ShyDB(models.Model):
    key = models.UUIDField(default=_default_uuid, primary_key=True)
    name = models.CharField(max_length=128, null=True, blank=True)
    value = models.JSONField(default=dict, blank=True)
    schema = models.JSONField(null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="db_entries")
    api_editable = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        pass

    def clean(self):
        if self.schema is not None and self.value is not None:
            try:
                v = Validator(self.schema)
                errors = sorted(v.iter_errors(self.value), key=lambda e: e.path)
            except Exception:
                raise ValidationError(
                    {"value": "Something went wrong. Check schema for errors."}
                )

            if errors:
                messages = [
                    "{}: {}".format(self._as_index(e.path), e.message) for e in errors
                ]
                raise ValidationError({"value": messages})

    def _as_index(self, path):
        path = path or []
        return f"Value[{']['.join(repr(index) for index in path)}]"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"({self.key}): {self.name}"
