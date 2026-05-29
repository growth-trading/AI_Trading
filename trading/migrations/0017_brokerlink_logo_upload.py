from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0016_remove_brokerservice'),
    ]

    operations = [
        migrations.RemoveField(model_name='brokerlink', name='logo_url'),
        migrations.AddField(
            model_name='brokerlink',
            name='logo',
            field=models.ImageField(blank=True, null=True, upload_to='broker_logos/', help_text='Upload ảnh logo sàn'),
        ),
    ]
