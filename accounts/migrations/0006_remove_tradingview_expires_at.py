from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_customuser_tradingview_expires_at'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customuser',
            name='tradingview_expires_at',
        ),
    ]
