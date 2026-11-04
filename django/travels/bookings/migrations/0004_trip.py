from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Step 1 of 3: add the Trip table and nullable trip links (nothing is removed yet)."""

    dependencies = [
        ('bookings', '0003_booking'),
    ]

    operations = [
        migrations.CreateModel(
            name='Trip',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('bus', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trips', to='bookings.bus')),
            ],
            options={
                'ordering': ['date'],
                'unique_together': {('bus', 'date')},
            },
        ),
        migrations.AddField(
            model_name='seat',
            name='trip',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='seats', to='bookings.trip'),
        ),
        migrations.AddField(
            model_name='booking',
            name='trip',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='bookings.trip'),
        ),
    ]
