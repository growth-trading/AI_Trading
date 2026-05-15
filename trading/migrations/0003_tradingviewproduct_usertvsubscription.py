from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0002_remove_coins_charged'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TradingViewProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(unique=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('chart_id', models.CharField(help_text='TradingView chart ID from URL', max_length=50)),
                ('symbol', models.CharField(default='OANDA:XAUUSD', max_length=50)),
                ('interval', models.CharField(default='60', max_length=10)),
                ('week_cost', models.PositiveIntegerField(default=10)),
                ('month_cost', models.PositiveIntegerField(default=30)),
                ('year_cost', models.PositiveIntegerField(default=200)),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                'ordering': ['sort_order', 'pk'],
            },
        ),
        migrations.CreateModel(
            name='UserTVSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('expires_at', models.DateTimeField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tv_subscriptions', to=settings.AUTH_USER_MODEL)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trading.tradingviewproduct')),
            ],
            options={
                'unique_together': {('user', 'product')},
            },
        ),
    ]
