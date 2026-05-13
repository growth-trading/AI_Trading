from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ChartAnalysisLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symbol', models.CharField(max_length=50)),
                ('interval', models.CharField(max_length=10)),
                ('signal', models.CharField(choices=[('BUY', 'BUY'), ('SELL', 'SELL'), ('HOLD', 'HOLD')], max_length=10)),
                ('confidence', models.IntegerField(default=0)),
                ('entry', models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ('sl', models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ('tp', models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ('reasoning', models.TextField(blank=True)),
                ('coins_charged', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='chart_analyses', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
