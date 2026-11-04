from django.contrib import admin
from .models import Bus,Seat,Booking,Trip


class BusAdmin(admin.ModelAdmin):
    list_display = ('bus_name','number','origin','destination')


class TripAdmin(admin.ModelAdmin):
    list_display = ('bus','date')
    list_filter = ('date',)


class SeatAdmin(admin.ModelAdmin):
    list_display = ('seat_number','trip','is_booked')
    list_filter = ('trip__date',)

class BookingAdmin(admin.ModelAdmin):
    list_display = ('user','trip','seat','booking_time')

# Register your models here.
admin.site.register(Bus, BusAdmin)
admin.site.register(Trip, TripAdmin)
admin.site.register(Seat,SeatAdmin)
admin.site.register(Booking, BookingAdmin)
