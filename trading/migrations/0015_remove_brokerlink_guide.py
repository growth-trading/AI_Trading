from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0014_remove_brokerlink_stats'),
    ]

    operations = [
        migrations.RemoveField(model_name='brokerlink', name='guide'),
        migrations.RemoveField(model_name='brokerlink', name='guide_en'),
    ]
