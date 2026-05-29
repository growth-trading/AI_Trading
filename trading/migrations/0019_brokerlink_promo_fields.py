from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0018_remove_hero_image_url'),
    ]

    operations = [
        migrations.AddField(model_name='brokerlink', name='promo_pct',
            field=models.CharField(blank=True, max_length=20, help_text='VD: 100%')),
        migrations.AddField(model_name='brokerlink', name='promo_subline',
            field=models.CharField(blank=True, max_length=100, help_text='VD: HÀNG NGÀY LÊN TỚI $14.4')),
        migrations.AddField(model_name='brokerlink', name='promo_subline_en',
            field=models.CharField(blank=True, max_length=100, help_text='VD: DAILY UP TO $14.4')),
    ]
