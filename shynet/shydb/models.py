from django.db import models
from core.models import User, _default_uuid


class ShyDB(models.Model):
    key = models.UUIDField(default=_default_uuid, primary_key=True)
    name = models.TextField(null=True, blank=True)
    value = models.JSONField(null=True, blank=True)
    schema = models.JSONField(null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="db_entries")
    api_editable = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        pass

    def __str__(self):
        return f'({self.key}): {self.name}'
