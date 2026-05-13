from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_customuser_address_customuser_phone'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='ai_trading_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
