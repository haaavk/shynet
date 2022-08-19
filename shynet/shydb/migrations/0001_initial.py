# Generated by Django 3.2.12 on 2022-08-19 09:19

import core.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ShyDB',
            fields=[
                ('key', models.UUIDField(default=core.models._default_uuid, primary_key=True, serialize=False)),
                ('name', models.TextField(blank=True, null=True)),
                ('value', models.JSONField(blank=True, null=True)),
                ('schema', models.JSONField(blank=True, null=True)),
                ('api_editable', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='db_entries', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
