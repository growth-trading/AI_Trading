from django.db import migrations


def create_initial_products(apps, schema_editor):
    TradingViewProduct = apps.get_model('trading', 'TradingViewProduct')
    TradingViewProduct.objects.bulk_create([
        TradingViewProduct(
            slug='xauusd-h1',
            name='XAUUSD H1 — Phân tích Vàng',
            description='Biểu đồ vàng khung H1 với đầy đủ indicator MACD, RSI, EMA, Supertrend. Phù hợp swing trading.',
            chart_id='lZgY7rP1',
            symbol='OANDA:XAUUSD',
            interval='60',
            week_cost=10,
            month_cost=30,
            year_cost=200,
            sort_order=0,
        ),
        TradingViewProduct(
            slug='xauusd-m15',
            name='XAUUSD M15 — Scalping Vàng',
            description='Biểu đồ vàng khung M15 tối ưu cho scalping. Indicator tốc độ cao, tín hiệu vào lệnh nhanh.',
            chart_id='lZgY7rP1',
            symbol='OANDA:XAUUSD',
            interval='15',
            week_cost=10,
            month_cost=30,
            year_cost=200,
            sort_order=1,
        ),
        TradingViewProduct(
            slug='xauusd-d1',
            name='XAUUSD D1 — Phân tích Dài hạn',
            description='Biểu đồ vàng khung D1 với vùng hỗ trợ/kháng cự chính, phù hợp đầu tư trung và dài hạn.',
            chart_id='lZgY7rP1',
            symbol='OANDA:XAUUSD',
            interval='D',
            week_cost=10,
            month_cost=30,
            year_cost=200,
            sort_order=2,
        ),
    ])


def delete_initial_products(apps, schema_editor):
    TradingViewProduct = apps.get_model('trading', 'TradingViewProduct')
    TradingViewProduct.objects.filter(slug__in=['xauusd-h1', 'xauusd-m15', 'xauusd-d1']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0003_tradingviewproduct_usertvsubscription'),
    ]

    operations = [
        migrations.RunPython(create_initial_products, delete_initial_products),
    ]
