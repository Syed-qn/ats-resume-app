# Generated by Django 4.2.7 on 2025-06-01 10:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resume', '0004_manual_resume_models'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='skill',
            name='unique_skill_per_resume',
        ),
        migrations.AlterUniqueTogether(
            name='skill',
            unique_together={('resume', 'name')},
        ),
    ]
