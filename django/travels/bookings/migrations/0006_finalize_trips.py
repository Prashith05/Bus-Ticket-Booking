from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Step 3 of 3: every seat and booking now has a trip, so make the link required
    and drop the old direct links to Bus."""

    dependencies = [
        ('bookings', '0005_populate_trips'),
    ]

    operations = [
        migrations.AlterField(
            model_name='seat',
            name='trip',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='seats', to='bookings.trip'),
        ),
        migrations.AlterField(
            model_name='booking',
            name='trip',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bookings.trip'),
        ),
        migrations.RemoveField(
            model_name='seat',
            name='bus',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='bus',
        ),
        migrations.AlterUniqueTogether(
            name='seat',
            unique_together={('trip', 'seat_number')},
        ),
    ]
