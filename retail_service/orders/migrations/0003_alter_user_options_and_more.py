# Generated by Django 5.1.1 on 2024-09-16 11:49

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0002_productinfo_external_id"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="user",
            options={
                "ordering": ["email"],
                "verbose_name": "User",
                "verbose_name_plural": "User list",
            },
        ),
        migrations.AlterField(
            model_name="confirmemailtoken",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Creation date"),
        ),
        migrations.AlterField(
            model_name="confirmemailtoken",
            name="key",
            field=models.CharField(
                db_index=True, max_length=64, unique=True, verbose_name="Key"
            ),
        ),
        migrations.AlterField(
            model_name="confirmemailtoken",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="confirm_email_tokens",
                to=settings.AUTH_USER_MODEL,
                verbose_name="User associated with the confirmation token",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("basket", "Basket status"),
                    ("new", "New"),
                    ("confirmed", "Confirmed"),
                    ("assembled", "Assembled"),
                    ("sent", "Sent"),
                    ("delivered", "Delivered"),
                    ("canceled", "Canceled"),
                ],
                max_length=15,
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="company",
            field=models.CharField(blank=True, max_length=40, verbose_name="Company"),
        ),
        migrations.AlterField(
            model_name="user",
            name="first_name",
            field=models.CharField(
                blank=True, max_length=30, verbose_name="First name"
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="last_name",
            field=models.CharField(
                blank=True, max_length=150, verbose_name="Last name"
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="position",
            field=models.CharField(blank=True, max_length=40, verbose_name="Position"),
        ),
        migrations.AlterField(
            model_name="user",
            name="type",
            field=models.CharField(
                choices=[("shop", "Shop"), ("buyer", "Buyer")],
                default="buyer",
                max_length=5,
                verbose_name="User type",
            ),
        ),
    ]
