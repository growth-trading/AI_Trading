from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0012_add_broker_link'),
    ]

    operations = [
        migrations.DeleteModel(name='BrokerLink'),
        migrations.CreateModel(
            name='BrokerService',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField(unique=True)),
                ('logo_url', models.URLField(blank=True, help_text='URL logo dịch vụ')),
                ('tagline', models.CharField(blank=True, max_length=200, help_text='Slogan ngắn (Tiếng Việt)')),
                ('tagline_en', models.CharField(blank=True, max_length=200)),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Dịch vụ',
                'verbose_name_plural': 'Dịch vụ',
                'ordering': ['sort_order', 'pk'],
            },
        ),
        migrations.CreateModel(
            name='BrokerLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='brokers', to='trading.brokerservice')),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField(max_length=50)),
                ('logo_url', models.URLField(blank=True, help_text='URL logo sàn')),
                ('hero_image_url', models.URLField(blank=True, help_text='URL ảnh banner bên phải hero section')),
                ('hero_title', models.CharField(blank=True, max_length=200, help_text='VD: EXNESS REBATES')),
                ('hero_title_en', models.CharField(blank=True, max_length=200)),
                ('category', models.CharField(
                    choices=[('forex', 'Forex'), ('crypto', 'Crypto'), ('cfd', 'CFD'), ('stock', 'Chứng khoán'), ('other', 'Khác')],
                    default='forex', max_length=20,
                )),
                ('register_url', models.URLField(help_text='Link đăng ký IB/affiliate')),
                ('partner_code', models.CharField(blank=True, max_length=100, help_text='Mã đối tác, VD: backcomio')),
                ('description', models.TextField(blank=True, help_text='Mô tả chương trình (Tiếng Việt)')),
                ('description_en', models.TextField(blank=True)),
                ('stats', models.JSONField(blank=True, default=list, help_text='VD: [{"icon":"bi-percent","value":"100%","label":"Tỉ Lệ Chiết Khấu","label_en":"Rebate Rate"}]')),
                ('partner_level', models.CharField(blank=True, max_length=50, help_text='VD: Kim cương')),
                ('partner_level_en', models.CharField(blank=True, max_length=50)),
                ('partner_level_date', models.CharField(blank=True, max_length=50, help_text='VD: Đến 28 Th03, 2026')),
                ('rebate_standard', models.CharField(blank=True, max_length=20, help_text='VD: 40%')),
                ('rebate_pro', models.CharField(blank=True, max_length=20, help_text='VD: 25%')),
                ('rebate_raw', models.CharField(blank=True, max_length=100, help_text='VD: Cố định trên mỗi lô')),
                ('rebate_raw_en', models.CharField(blank=True, max_length=100)),
                ('guide', models.TextField(blank=True, help_text='Nội dung hướng dẫn (HTML, Tiếng Việt)')),
                ('guide_en', models.TextField(blank=True, help_text='English guide (HTML)')),
                ('rebate_table', models.TextField(blank=True, help_text='Bảng hoàn phí (HTML)')),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Broker / Sàn giao dịch',
                'verbose_name_plural': 'Brokers / Sàn giao dịch',
                'ordering': ['sort_order', 'pk'],
                'unique_together': {('service', 'slug')},
            },
        ),
    ]
