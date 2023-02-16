# Generated by Django 4.1.7 on 2023-02-16 12:06

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('support_app', '0007_owner_alter_botuser_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='creds',
            field=models.CharField(blank=True, max_length=2000, verbose_name='доступы к сервису'),
        ),
        migrations.AddField(
            model_name='order',
            name='estimated_hours',
            field=models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(24)], verbose_name='оцененное время выполнения в часах'),
        ),
    ]
