from django.urls import path
from . import views

urlpatterns = [

    path('select-seats/<int:showtime_id>/', views.select_seats, name='select_seats'),
    

    path('api/reserve-seats/<int:showtime_id>/', views.reserve_seats, name='reserve_seats'),
    path('api/release-seats/<int:showtime_id>/', views.release_seats, name='release_seats'),
    path('api/seat-status/<int:showtime_id>/', views.get_seat_status, name='get_seat_status'),
    

    path('summary/<int:showtime_id>/', views.booking_summary, name='booking_summary'),
    

    path('api/create-booking/<int:showtime_id>/', views.create_booking, name='create_booking'),
    

    path('<int:booking_id>/payment/', views.payment_page, name='payment_page'),
    path('<int:booking_id>/payment/success/', views.payment_success, name='payment_success'),
    path('<int:booking_id>/payment/failed/', views.payment_failed, name='payment_failed'),
    path('razorpay-webhook/', views.razorpay_webhook, name='razorpay_webhook'),
    

    path('api/cancel/<int:booking_id>/', views.cancel_booking_api, name='cancel_booking'),
    path('beacon/release/<int:booking_id>/', views.release_booking_beacon, name='release_booking_beacon'),
    

    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('detail/<int:booking_id>/', views.booking_detail, name='booking_detail'),
]