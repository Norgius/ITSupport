# Generated by Django 4.1.7 on 2023-02-15 15:49

import django.core.validators
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('support_app', '0005_alter_order_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='SystemSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('parameter_name', models.CharField(help_text='желательно задавать на английском и без пробелов', max_length=100, verbose_name='имя системного параметра')),
                ('parameter_value', models.TextField(blank=True, help_text='может быть пустой строкой, тогда метод которому это нужно сам придумает дефолт', verbose_name='значение системного параметра')),
                ('description', models.TextField(verbose_name='описание параметра')),
            ],
        ),
        migrations.AddField(
            model_name='botuser',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='дата и время создания'),
        ),
        migrations.AddField(
            model_name='tariff',
            name='price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8, validators=[django.core.validators.MinValueValidator(0)], verbose_name='цена'),
            preserve_default=False,
        ),
    ]
