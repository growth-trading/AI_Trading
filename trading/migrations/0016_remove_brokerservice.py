from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0015_remove_brokerlink_guide'),
    ]

    operations = [
        migrations.AlterUniqueTogether(name='brokerlink', unique_together=set()),
        migrations.RemoveField(model_name='brokerlink', name='service'),
        migrations.AlterField(
            model_name='brokerlink',
            name='slug',
            field=models.SlugField(max_length=50, unique=True),
        ),
        migrations.DeleteModel(name='BrokerService'),
    ]
