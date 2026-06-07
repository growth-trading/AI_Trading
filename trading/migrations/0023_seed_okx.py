from django.db import migrations


def seed_okx(apps, schema_editor):
    BrokerLink = apps.get_model('trading', 'BrokerLink')
    BrokerLink.objects.get_or_create(
        slug='okx',
        defaults={
            'name': 'OKX',
            'category': 'crypto',
            'register_url': 'https://okx.com/join/77790016',
            'partner_code': '77790016',
            'is_active': True,
            'sort_order': 4,
        },
    )


def unseed_okx(apps, schema_editor):
    BrokerLink = apps.get_model('trading', 'BrokerLink')
    BrokerLink.objects.filter(slug='okx').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0022_seed_bybit'),
    ]

    operations = [
        migrations.RunPython(seed_okx, unseed_okx),
    ]
