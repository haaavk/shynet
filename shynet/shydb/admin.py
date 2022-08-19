from django.contrib import admin

# from django_json_widget.widgets import JSONEditorWidget

from .models import ShyDB


@admin.register(ShyDB)
class ShyDBAdmin(admin.ModelAdmin):
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['-updated_at']
    # formfield_overrides = {
    # models.JSONField: {'widget': JSONEditorWidget},
    # }
