from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0013_brokerservice_refactor_brokerlink'),
    ]

    operations = [
        migrations.RemoveField(model_name='brokerlink', name='stats'),
    ]
