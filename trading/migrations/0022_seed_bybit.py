from django.db import migrations


def seed_bybit(apps, schema_editor):
    BrokerLink = apps.get_model('trading', 'BrokerLink')
    BrokerLink.objects.get_or_create(
        slug='bybit',
        defaults={
            'name': 'Bybit',
            'category': 'crypto',
            'register_url': 'https://www.bybitglobal.com/invite?ref=RBZN7O',
            'partner_code': 'RBZN7O',
            'is_active': True,
            'sort_order': 3,
        },
    )


def unseed_bybit(apps, schema_editor):
    BrokerLink = apps.get_model('trading', 'BrokerLink')
    BrokerLink.objects.filter(slug='bybit').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0021_seed_brokerlinks'),
    ]

    operations = [
        migrations.RunPython(seed_bybit, unseed_bybit),
    ]
