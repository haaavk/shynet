from django.db import models
from core.models import User, _default_uuid
from django.core.exceptions import ValidationError


from cerberus import Validator


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
            v = Validator(self.schema)
            if not v.validate(self.value):
                raise ValidationError({"value": str(v.errors)})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"({self.key}): {self.name}"
