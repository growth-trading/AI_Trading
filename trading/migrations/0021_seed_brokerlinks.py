from django.db import migrations


def seed_brokers(apps, schema_editor):
    BrokerLink = apps.get_model('trading', 'BrokerLink')
    brokers = [
        {
            'name': 'Exness',
            'slug': 'exness',
            'category': 'forex',
            'register_url': 'https://www.exness.com/',
            'partner_code': '',
            'is_active': True,
            'sort_order': 1,
        },
        {
            'name': 'Binance',
            'slug': 'binance',
            'category': 'crypto',
            'register_url': 'https://www.binance.com/referral/earn-together/refer2earn-usdc/claim?hl=vi&ref=GRO_28502_OY2W6&utm_source=referral_entrance',
            'partner_code': 'GRO_28502_OY2W6',
            'is_active': True,
            'sort_order': 2,
        },
    ]
    for data in brokers:
        BrokerLink.objects.get_or_create(slug=data['slug'], defaults=data)


def unseed_brokers(apps, schema_editor):
    BrokerLink = apps.get_model('trading', 'BrokerLink')
    BrokerLink.objects.filter(slug__in=['exness', 'binance']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0020_simplify_brokerlink'),
    ]

    operations = [
        migrations.RunPython(seed_brokers, unseed_brokers),
    ]
