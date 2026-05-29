from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0017_brokerlink_logo_upload'),
    ]

    operations = [
        migrations.RemoveField(model_name='brokerlink', name='hero_image_url'),
    ]
