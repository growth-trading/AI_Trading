from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0019_brokerlink_promo_fields'),
    ]

    operations = [
        migrations.RemoveField(model_name='brokerlink', name='hero_title'),
        migrations.RemoveField(model_name='brokerlink', name='hero_title_en'),
        migrations.RemoveField(model_name='brokerlink', name='description'),
        migrations.RemoveField(model_name='brokerlink', name='description_en'),
        migrations.RemoveField(model_name='brokerlink', name='promo_pct'),
        migrations.RemoveField(model_name='brokerlink', name='promo_subline'),
        migrations.RemoveField(model_name='brokerlink', name='promo_subline_en'),
        migrations.RemoveField(model_name='brokerlink', name='partner_level'),
        migrations.RemoveField(model_name='brokerlink', name='partner_level_en'),
        migrations.RemoveField(model_name='brokerlink', name='partner_level_date'),
        migrations.RemoveField(model_name='brokerlink', name='rebate_standard'),
        migrations.RemoveField(model_name='brokerlink', name='rebate_pro'),
        migrations.RemoveField(model_name='brokerlink', name='rebate_raw'),
        migrations.RemoveField(model_name='brokerlink', name='rebate_raw_en'),
        migrations.RemoveField(model_name='brokerlink', name='rebate_table'),
    ]
