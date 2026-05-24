from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def copy_amount_to_committed(apps, schema_editor):
    """Copy old 'amount' field values to new 'amount_committed' field."""
    Investment = apps.get_model("investors", "Investment")
    for inv in Investment.objects.all():
        inv.amount_committed = inv.amount if inv.amount else Decimal("0.01")
        inv.save(update_fields=["amount_committed"])


def copy_investor_from_profile(apps, schema_editor):
    """Copy investor_profile.user to new 'investor' field."""
    Investment = apps.get_model("investors", "Investment")
    for inv in Investment.objects.all():
        if inv.investor_profile_id:
            inv.investor_id = inv.investor_profile.user_id
            inv.save(update_fields=["investor_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("investors", "0004_saveditem_saveditem_unique_saved_item"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="investment",
            name="amount_committed",
            field=models.DecimalField(
                decimal_places=2, max_digits=14, null=True, blank=True
            ),
        ),
        migrations.RunPython(copy_amount_to_committed, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="investment",
            name="amount_committed",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=14,
                validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
            ),
        ),
        migrations.RemoveField(model_name="investment", name="amount"),
        migrations.AddField(
            model_name="investment",
            name="amount_invested",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=14, null=True
            ),
        ),
        migrations.AddField(
            model_name="investment",
            name="currency",
            field=models.CharField(default="UAH", max_length=3),
        ),
        migrations.AddField(
            model_name="investment",
            name="status",
            field=models.CharField(
                choices=[
                    ("committed", "Committed"),
                    ("confirmed", "Confirmed"),
                    ("cancelled", "Cancelled"),
                ],
                default="committed",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="investment",
            name="meta",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="investment",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="investment",
            name="investor",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="investments",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(copy_investor_from_profile, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="investment",
            name="investor",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="investments",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RemoveField(model_name="investment", name="investor_profile"),
        migrations.AlterField(
            model_name="investment",
            name="project",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="investments",
                to="projects.project",
            ),
        ),
    ]
