from django.core.management.base import BaseCommand
from django.conf import settings

template = """
#!/bin/bash

FILE_PATH="{file_path}"
DB_NAME="{db_name}"
FTP_ADDRESS="{ftp_address}"
FTP_USER="{ftp_user}"

pg_dump --dbname=$DB_NAME | gzip > $FILE_PATH
curl --upload-file $FILE_PATH $FTP_ADDRESS --user $FTP_USER

exit 0
"""


class Command(BaseCommand):
    help = "Generate backup script"

    def handle(self, *args, **options):
        kwargs = {
            "file_path": settings.BACKUP_SCRIPT_FILE_PATH,
            "db_name": settings.BACKUP_SCRIPT_DB_NAME,
            "ftp_address": settings.BACKUP_SCRIPT_FTP_ADDRESS,
            "ftp_user": settings.BACKUP_SCRIPT_FTP_USER,
        }
        script = template.format(**kwargs).strip()
        print(script)
