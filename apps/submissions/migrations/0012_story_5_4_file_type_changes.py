# -*- coding: utf-8 -*-
"""
Story 5.4: Data migration to update COB file type values

Changes:
- OPIS_INICIJATIVE → BUDZET_INICIJATIVE
- PISMO_NAMERE → PISMO_PODRSKE

Also updates the choices in FileMetadata.file_type field.
"""

from django.db import migrations, models


def update_file_types_forward(apps, schema_editor):
    """
    Update existing FileMetadata records with new file_type values.
    """
    FileMetadata = apps.get_model('submissions', 'FileMetadata')

    # Update OPIS_INICIJATIVE to BUDZET_INICIJATIVE
    FileMetadata.objects.filter(file_type='OPIS_INICIJATIVE').update(
        file_type='BUDZET_INICIJATIVE'
    )

    # Update PISMO_NAMERE to PISMO_PODRSKE
    FileMetadata.objects.filter(file_type='PISMO_NAMERE').update(
        file_type='PISMO_PODRSKE'
    )


def update_file_types_reverse(apps, schema_editor):
    """
    Reverse migration: restore original file_type values.
    """
    FileMetadata = apps.get_model('submissions', 'FileMetadata')

    # Restore BUDZET_INICIJATIVE to OPIS_INICIJATIVE
    FileMetadata.objects.filter(file_type='BUDZET_INICIJATIVE').update(
        file_type='OPIS_INICIJATIVE'
    )

    # Restore PISMO_PODRSKE to PISMO_NAMERE
    FileMetadata.objects.filter(file_type='PISMO_PODRSKE').update(
        file_type='PISMO_NAMERE'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0011_story_5_3_initiative_new_fields'),
    ]

    operations = [
        # Data migration to update existing file_type values
        migrations.RunPython(
            update_file_types_forward,
            update_file_types_reverse,
        ),

        # Update the choices in the FileMetadata model (increased max_length for new values)
        migrations.AlterField(
            model_name='filemetadata',
            name='file_type',
            field=models.CharField(
                choices=[
                    ('BUDGET', 'Budžet'),
                    ('BIOGRAPHY', 'Biografija'),
                    ('SUPPORT_LETTER', 'Pismo Podrške'),
                    ('BUDZET_INICIJATIVE', 'Budžet Inicijative'),
                    ('PISMO_PODRSKE', 'Pismo Podrške'),
                ],
                max_length=20,
                verbose_name='Tip Fajla',
            ),
        ),
    ]
