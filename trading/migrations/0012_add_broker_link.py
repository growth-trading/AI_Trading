from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0011_add_is_coming_soon'),
    ]

    operations = [
        migrations.CreateModel(
            name='BrokerLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('name_en', models.CharField(blank=True, max_length=100)),
                ('logo_url', models.URLField(blank=True, help_text='URL ảnh logo sàn')),
                ('description', models.TextField(blank=True)),
                ('description_en', models.TextField(blank=True)),
                ('register_url', models.URLField(help_text='Link đăng ký IB/affiliate của sàn')),
                ('category', models.CharField(
                    choices=[('forex', 'Forex'), ('crypto', 'Crypto'), ('cfd', 'CFD'), ('stock', 'Chứng khoán'), ('other', 'Khác')],
                    default='forex', max_length=20,
                )),
                ('badge', models.CharField(blank=True, help_text='Nhãn hiển thị, VD: Khuyên dùng, Hot', max_length=30)),
                ('badge_en', models.CharField(blank=True, max_length=30)),
                ('features', models.TextField(blank=True, help_text='Mỗi dòng = 1 tính năng (Tiếng Việt)')),
                ('features_en', models.TextField(blank=True, help_text='English features, one per line')),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Broker / Sàn giao dịch',
                'verbose_name_plural': 'Brokers / Sàn giao dịch',
                'ordering': ['sort_order', 'pk'],
            },
        ),
    ]
