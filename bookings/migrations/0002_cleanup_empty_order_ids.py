# Generated manually for cleaning up empty razorpay_order_id values

from django.db import migrations


def cleanup_empty_order_ids(apps, schema_editor):
    """Give unique placeholder values to empty razorpay_order_id so migration can proceed"""
    import uuid
    Booking = apps.get_model('bookings', 'Booking')
    
    # Give each empty booking a unique temporary value
    empty_bookings = Booking.objects.filter(razorpay_order_id='')
    for booking in empty_bookings:
        booking.razorpay_order_id = f'temp_{uuid.uuid4().hex[:16]}'
        booking.save()
    
    print(f"Assigned temporary IDs to {empty_bookings.count()} bookings with empty order_id")


def reverse_cleanup(apps, schema_editor):
    """Reverse operation - remove temporary IDs"""
    Booking = apps.get_model('bookings', 'Booking')
    
    # Set temp IDs back to empty (but this shouldn't happen in practice)
    Booking.objects.filter(razorpay_order_id__startswith='temp_').update(razorpay_order_id='')


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(cleanup_empty_order_ids, reverse_cleanup),
    ]
