from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_http_methods, require_POST
from django.utils import timezone
import json
import logging
from .razorpay_utils import razorpay_client
from .email_utils import send_booking_confirmation_email
from django.http import HttpResponse
from movies.models import Movie
from movies.theater_models import Showtime
from .models import Booking, Transaction
from .utils import SeatManager, PriceCalculator
from django.conf import settings
from accounts.decorators import email_verified_required

logger = logging.getLogger(__name__)

def supports_select_for_update():

    db_engine = settings.DATABASES['default']['ENGINE']
    return 'sqlite3' not in db_engine

@email_verified_required
def select_seats(request, showtime_id):

    showtime = get_object_or_404(Showtime, id=showtime_id, is_active=True)
    
    if showtime.date < timezone.now().date():
        messages.error(request, 'This showtime has already passed.')
        return redirect('movie_detail', slug=showtime.movie.slug)
    
    seat_layout = SeatManager.get_seat_layout(showtime_id)
    reserved_seats = SeatManager.get_reserved_seats(showtime_id)
    available_seats = SeatManager.get_available_seats(showtime_id)
    
    for row in seat_layout:
        for seat in row:
            if seat:
                if seat['seat_id'] in reserved_seats:
                    seat['status'] = 'reserved'
                elif seat['seat_id'] in available_seats:
                    seat['status'] = 'available'
                else:
                    seat['status'] = 'booked'
    
    context = {
        'showtime': showtime,
        'movie': showtime.movie,
        'seat_layout': seat_layout,
        'screen': showtime.screen,
        'max_seats': 10,
    }
    
    return render(request, 'bookings/select_seats.html', context)

@login_required
@require_POST
def reserve_seats(request, showtime_id):

    try:
        data = json.loads(request.body)
        seat_ids = data.get('seat_ids', [])
        
        if not seat_ids:
            return JsonResponse({'error': 'No seats selected'}, status=400)
        
        if len(seat_ids) > 10:
            return JsonResponse({'error': 'Maximum 10 seats allowed per booking'}, status=400)
        
        reservation = request.session.get('seat_reservation', {})
        reservation[str(showtime_id)] = seat_ids
        request.session['seat_reservation'] = reservation 
        
        return JsonResponse({
            'success': True,
            'message': 'Seats selected',
            'seat_ids': seat_ids
        })
            
    except Exception as e:
        logger.error(f"Error reserving seats for showtime {showtime_id}: {str(e)}")
        return JsonResponse({'error': 'Failed to reserve seats. Please try again.'}, status=500)

@login_required
@require_POST
def release_seats(request, showtime_id):

    try:
        SeatManager.release_seats(showtime_id, user_id=request.user.id)
        reservation = request.session.get('seat_reservation', {})
        if str(showtime_id) in reservation:
            del reservation[str(showtime_id)]
            request.session['seat_reservation'] = reservation
            
        return JsonResponse({'success': True, 'message': 'Seats released'})
    except Exception as e:
        logger.error(f"Error releasing seats for showtime {showtime_id}: {str(e)}")
        return JsonResponse({'error': 'Failed to release seats.'}, status=500)

def get_seat_status(request, showtime_id):

    try:
        reserved_seats = SeatManager.get_reserved_seats(showtime_id)
        available_seats = SeatManager.get_available_seats(showtime_id)
        
        seat_layout = SeatManager.get_seat_layout(showtime_id)
        all_seats = []
        for row in seat_layout:
            for seat in row:
                if seat:
                    all_seats.append(seat['seat_id'])
        
        booked_seats = [s for s in all_seats if s not in available_seats and s not in reserved_seats]
        
        response = JsonResponse({
            'success': True,
            'reserved_seats': reserved_seats,
            'booked_seats': booked_seats,
            'available_count': len(available_seats)
        })
        
        # Add no-cache headers to prevent browser/Django from caching seat status
        # This is crucial for real-time seat availability updates after payment modal closes
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response
    except Exception as e:
        logger.error(f"Error getting seat status for showtime {showtime_id}: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Failed to get seat status.'}, status=500)

@login_required
def booking_summary(request, showtime_id):

    showtime = get_object_or_404(Showtime, id=showtime_id)
    
    reservation = request.session.get('seat_reservation', {})
    
    if not reservation or str(showtime_id) not in reservation:
        messages.error(request, 'No seats reserved. Please select seats first.')
        return redirect('select_seats', showtime_id=showtime_id)
    
    seat_ids = reservation[str(showtime_id)]
    
    price_details = PriceCalculator.calculate_booking_amount(
        showtime, 
        len(seat_ids)
    )
    
    from django.core.cache import cache
    cache_key = f"seat_reservation_{showtime_id}_{request.user.id}"
    remaining_seconds = cache.ttl(cache_key)
    
    context = {
        'showtime': showtime,
        'movie': showtime.movie,
        'seat_ids': seat_ids,
        'seat_count': len(seat_ids),
        'price_details': price_details,
        'total_amount': price_details['total_amount'],
        'expires_in_seconds': remaining_seconds if remaining_seconds > 0 else 600,
    }
    
    return render(request, 'bookings/booking_summary.html', context)

@login_required
@require_POST
def create_booking(request, showtime_id):

    try:
        showtime = get_object_or_404(Showtime, id=showtime_id)
        data = json.loads(request.body)
        seat_ids = data.get('seat_ids', [])
        
        existing_pending = Booking.objects.filter(
            user=request.user,
            showtime=showtime,
            status='PENDING'
        )
        for old_booking in existing_pending:
            logger.info(f"🧹 Cancelling existing PENDING booking {old_booking.booking_number} before creating new one")
            old_booking.status = 'CANCELLED'
            old_booking.save()
            SeatManager.release_seats(showtime_id, old_booking.seats, user_id=request.user.id)
        
        success = SeatManager.reserve_seats(showtime_id, seat_ids, request.user.id)
        
        if not success:
             print(f"⚠️ SAFETY CHECK FAILED: User {request.user.id} tried to book seats {seat_ids} for showtime {showtime_id} but they were already taken.")
             return JsonResponse({
                 'success': False,
                 'error': 'Oh no! One or more of these seats were just taken by another user.'
             }, status=400)
        
        price_details = PriceCalculator.calculate_booking_amount(showtime, len(seat_ids))
        
        booking = Booking.objects.create(
            user=request.user,
            showtime=showtime,
            seats=seat_ids,
            total_seats=len(seat_ids),
            base_price=price_details['base_price'],
            convenience_fee=price_details['convenience_fee'],
            tax_amount=price_details['tax_amount'],
            total_amount=price_details['total_amount'],
            status='PENDING'
        )
        
        order_data = razorpay_client.create_order(
            amount=booking.total_amount,
            receipt=f"booking_{booking.booking_number}"
        )
        
        if not order_data['success']:
            return JsonResponse({
                'success': False, 
                'error': f"Payment Gateway Error: {order_data['error']}"
            }, status=500)

        booking.razorpay_order_id = order_data['order_id']
        booking.payment_initiated_at = timezone.now()
        booking.save()

        return JsonResponse({
            'success': True,
            'booking_id': booking.id,
            'booking_number': booking.booking_number,
            'total_amount': float(booking.total_amount),
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'order_id': order_data['order_id'],
            'amount': order_data['amount'],
            'currency': order_data['currency'],
            'is_mock': order_data.get('is_mock', False),
            'redirect_url': f'/bookings/{booking.id}/payment/' # Fallback
        })
        
    except Exception as e:
        logger.error(f"Error creating booking for showtime {showtime_id}: {str(e)}")
        return JsonResponse({'error': 'Failed to create booking. Please try again.'}, status=500)

@login_required
def payment_page(request, booking_id):

    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    session_key = f'payment_page_visited_{booking_id}'
    
    if request.session.get(session_key):
        if booking.status == 'PENDING' and not booking.payment_received_at:
            logger.info(f"🔄 Payment page refresh detected for booking {booking.booking_number}. Cancelling and releasing seats.")
            booking.status = 'CANCELLED'
            booking.save()
            
            SeatManager.release_seats(booking.showtime.id, booking.seats, user_id=booking.user.id)
            
            del request.session[session_key]
            if 'seat_reservation' in request.session:
                reservation = request.session.get('seat_reservation', {})
                if str(booking.showtime.id) in reservation:
                    del reservation[str(booking.showtime.id)]
                    request.session['seat_reservation'] = reservation
            
            messages.warning(request, 'Your previous booking was cancelled due to page refresh. Please select seats again.')
            return redirect('select_seats', showtime_id=booking.showtime.id)
    
    request.session[session_key] = True
    
    if booking.is_expired():
        booking.status = 'EXPIRED'
        booking.save()
        SeatManager.release_seats(booking.showtime.id, booking.seats, user_id=booking.user.id)
        
        if session_key in request.session:
            del request.session[session_key]
        
        messages.error(request, 'Payment window expired. Please try again.')
        return redirect('select_seats', showtime_id=booking.showtime.id)
    
    order_data = razorpay_client.create_order(
        amount=booking.total_amount,
        receipt=f"booking_{booking.booking_number}"
    )
    
    if not order_data['success']:
        logger.error(f"Payment gateway error for booking {booking.booking_number}: {order_data.get('error', 'Unknown error')}")
        messages.error(request, "Payment gateway is temporarily unavailable. Please try again later.")
        return redirect('booking_summary', showtime_id=booking.showtime.id)

    context = {
        'booking': booking,
        'movie': booking.showtime.movie,
        'showtime': booking.showtime,
        'time_remaining': int((booking.expires_at - timezone.now()).total_seconds()) if booking.expires_at else 0,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'order_id': order_data['order_id'],
        'amount': order_data['amount'],
        'currency': order_data['currency'],
        'is_mock': order_data.get('is_mock', False),
    }
    
    return render(request, 'bookings/payment.html', context)

@login_required
def payment_success(request, booking_id):

    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    razorpay_payment_id = request.GET.get('razorpay_payment_id')
    razorpay_order_id = request.GET.get('razorpay_order_id')
    razorpay_signature = request.GET.get('razorpay_signature')
    
    if razorpay_order_id != booking.razorpay_order_id:
        messages.error(request, 'Payment mismatch. Please contact support.')
        return redirect('my_bookings')

    if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
        messages.error(request, 'Invalid payment response received.')
        return redirect('payment_page', booking_id=booking.id)
    
    is_valid = razorpay_client.verify_payment_signature(
        razorpay_order_id,
        razorpay_payment_id,
        razorpay_signature
    )
    
    if is_valid:
        payment_received_at = timezone.now()
        
        if payment_received_at > booking.expires_at:
            time_diff = (payment_received_at - booking.expires_at).total_seconds()
            
            booking.status = 'FAILED'
            booking.payment_id = razorpay_payment_id
            booking.payment_received_at = payment_received_at
            booking.save()
            
            logger.warning(
                f"⏰ LATE PAYMENT DETECTED: {booking.booking_number}\n"
                f"   ✅ Payment received at: {payment_received_at}\n"
                f"   ❌ Window expired at: {booking.expires_at}\n"
                f"   ⏱️  Lateness: {time_diff:.1f} seconds over deadline\n"
                f"   💳 Payment ID: {razorpay_payment_id}\n"
                f"   👤 User: {request.user.username}\n"
                f"   📊 Status set to: FAILED\n"
                f"   📧 Action: Refund email queued"
            )
            
            if not booking.refund_notification_sent:
                from .email_utils import send_late_payment_email
                send_late_payment_email(booking.id)
                logger.info(f"📧 Late payment refund email sent")
            else:
                logger.info(f"⏭️  Refund email already sent for booking {booking.booking_number}")
            
            messages.error(
                request, 
                f'⏰ Payment window expired ({int(time_diff)} seconds late). Your seats were released. '
                'Refund will be processed within 24 hours. Check your email for details.'
            )
            return redirect('select_seats', showtime_id=booking.showtime.id)
        
        is_still_valid = SeatManager.is_seat_still_available_for_user(
            booking.showtime.id, 
            booking.seats, 
            request.user.id
        )
        
        if not is_still_valid:
            booking.status = 'FAILED'
            booking.payment_id = razorpay_payment_id
            booking.save()
            
            SeatManager.release_seats(booking.showtime.id, booking.seats, user_id=booking.user.id)
            
            print(f"❌ BOOKING COLLISION: Payment received for {booking.booking_number} but seats were taken!")
            
            messages.error(request, 'Oh no! The seats were taken while you were paying. We have initiated an automatic refund.')
            return redirect('my_bookings')

        from django.db import transaction
        
        with transaction.atomic():
            if supports_select_for_update():
                booking = Booking.objects.select_for_update().get(id=booking.id)
            else:
                booking = Booking.objects.get(id=booking.id)
            
            if booking.status == 'CONFIRMED':
                logger.info(f"Booking {booking.booking_number} already confirmed, skipping duplicate processing")
                messages.success(request, f'Booking {booking.booking_number} confirmed!')
                return redirect('booking_detail', booking_id=booking.id)
            
            payment_received_at = timezone.now()
            booking.payment_received_at = payment_received_at
            booking.payment_id = razorpay_payment_id
            booking.payment_method = 'RAZORPAY'
            booking.status = 'CONFIRMED'
            booking.confirmed_at = timezone.now()
            
            booking.save()
        
        logger.info(f"✅ Booking {booking.booking_number} confirmed and payment received")
        
        SeatManager.confirm_seats(booking.showtime.id, booking.seats)
        
        session_key = f'payment_page_visited_{booking.id}'
        if session_key in request.session:
            del request.session[session_key]
        
        from .email_utils import send_booking_confirmation_email
        send_booking_confirmation_email(booking.id)
        
        messages.success(request, 'Ticket booked successfully!')
        return redirect('booking_detail', booking_id=booking.id)
    else:
        messages.error(request, 'Payment verification failed. Please contact support.')
        return redirect('my_bookings')

@login_required
def payment_failed(request, booking_id):

    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if booking.payment_received_at:
        logger.info(
            f"⏭️ payment_failed view called for {booking.booking_number}, "
            f"but payment_received_at is set. Redirecting to success page."
        )
        messages.success(request, 'Ticket booked successfully!')
        return redirect('booking_detail', booking_id=booking.id)
    
    booking.refresh_from_db()
    
    if booking.payment_received_at:
        logger.info(
            f"⏭️ After refresh, payment_received_at is set for {booking.booking_number}. "
            f"Payment succeeded, not sending failure email."
        )
        messages.success(request, 'Ticket booked successfully!')
        return redirect('booking_detail', booking_id=booking.id)
    
    if booking.status == 'PENDING':
        booking.status = 'FAILED'
        booking.save()
        
        SeatManager.release_seats(booking.showtime.id, booking.seats, user_id=booking.user.id)
        
        if not booking.failure_email_sent:
            from .email_utils import send_payment_failed_email
            send_payment_failed_email(booking.id)
    
    messages.error(request, 'Payment was unsuccessful. Your seats have been released.')
    return redirect('select_seats', showtime_id=booking.showtime.id)

@csrf_exempt
@require_POST
def razorpay_webhook(request):

    try:
        webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', None)
        if webhook_secret:
            webhook_signature = request.headers.get('X-Razorpay-Signature', '')
            if not razorpay_client.client.utility.verify_webhook_signature(
                request.body.decode('utf-8'),
                webhook_signature,
                webhook_secret
            ):
                logger.warning("Webhook signature verification failed")
                return HttpResponse(status=400)
        
        webhook_body = request.body.decode('utf-8')
        webhook_data = json.loads(webhook_body)
        
        event = webhook_data.get('event', '')
        payload = webhook_data.get('payload', {})
        payment_entity = payload.get('payment', {}).get('entity', {})
        
        order_id = payment_entity.get('order_id')
        payment_id = payment_entity.get('id')
        
        if event == 'payment.captured':
            try:
                booking = Booking.objects.get(razorpay_order_id=order_id)
                payment_received_at = timezone.now()
                
                if payment_received_at > booking.expires_at:
                    time_diff = (payment_received_at - booking.expires_at).total_seconds()
                    
                    booking.status = 'FAILED'
                    booking.payment_id = payment_id
                    booking.payment_received_at = payment_received_at
                    booking.save()
                    
                    SeatManager.release_seats(booking.showtime.id, booking.seats, user_id=booking.user.id)
                    
                    logger.warning(
                        f"⏰ WEBHOOK LATE PAYMENT DETECTED: {booking.booking_number}\n"
                        f"   ✅ Payment received at: {payment_received_at}\n"
                        f"   ❌ Window expired at: {booking.expires_at}\n"
                        f"   ⏱️  Lateness: {time_diff:.1f} seconds over deadline\n"
                        f"   💳 Payment ID: {payment_id}\n"
                        f"   📊 Status set to: FAILED\n"
                        f"   📧 Action: Refund email queued"
                    )
                    
                    if not booking.refund_notification_sent:
                        from .email_utils import send_late_payment_email
                        send_late_payment_email(booking.id)
                        logger.info(f"📧 Late payment refund email sent via webhook")
                    else:
                        logger.info(f"⏭️  Refund email already sent for booking {booking.booking_number} via webhook")
                    
                    return HttpResponse(status=200)
                
                if booking.status == 'PENDING':
                    booking.refresh_from_db()
                    
                    if booking.payment_received_at:
                        logger.info(f"⏭️  WEBHOOK: Booking {booking.booking_number} already has payment_received_at. Skipping.")
                        return HttpResponse(status=200)
                    
                    booking.payment_received_at = payment_received_at
                    booking.payment_id = payment_id
                    booking.status = 'CONFIRMED'
                    booking.confirmed_at = timezone.now()
                    booking.save()
                    
                    SeatManager.confirm_seats(booking.showtime.id, booking.seats)
                    
                    from .email_utils import send_booking_confirmation_email
                    send_booking_confirmation_email(booking.id)
                    logger.info(f"✅ WEBHOOK: Confirmation email sent for booking {booking.booking_number}")
                elif booking.status == 'CONFIRMED':
                    logger.info(f"⏭️  WEBHOOK: Booking {booking.booking_number} already confirmed. Skipping.")
                else:
                    logger.info(f"⏭️  WEBHOOK: Booking {booking.booking_number} is {booking.status}. Skipping.")
            except Booking.DoesNotExist:
                logger.error(f"⚠️ Webhook: Booking not found for order {order_id}")
                pass
                
        return HttpResponse(status=200)
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return HttpResponse(status=400)

@login_required
@email_verified_required
def my_bookings(request):

    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'bookings': bookings,
        'now': timezone.now(),
    }
    
    return render(request, 'bookings/my_bookings.html', context)

@email_verified_required
def booking_detail(request, booking_id):

    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    context = {
        'booking': booking,
        'movie': booking.showtime.movie,
        'showtime': booking.showtime,
        'theater': booking.showtime.screen.theater,
    }
    
    return render(request, 'bookings/booking_detail.html', context)

@login_required
@require_POST
def cancel_booking_api(request, booking_id):

    try:
        from django.db import transaction
        
        with transaction.atomic():
            if supports_select_for_update():
                booking = get_object_or_404(
                    Booking.objects.select_for_update(), 
                    id=booking_id, 
                    user=request.user
                )
            else:
                booking = get_object_or_404(
                    Booking, 
                    id=booking_id, 
                    user=request.user
                )
            
            if booking.status != 'PENDING':
                return JsonResponse({
                    'success': False,
                    'error': f'Cannot cancel booking with status: {booking.status}'
                }, status=400)
            
            if booking.payment_received_at:
                return JsonResponse({
                    'success': False,
                    'error': 'Payment already received - booking cannot be cancelled',
                    'booking_id': booking.id
                }, status=400)
            
            data = json.loads(request.body) if request.body else {}
            reason = data.get('reason', 'User cancelled booking')
            showtime_id = booking.showtime.id
            
            booking.status = 'FAILED'
            booking.save()
        
        if not booking.failure_email_sent:
            from .email_utils import send_payment_failed_email
            send_payment_failed_email(booking.id)
        
        SeatManager.release_seats(showtime_id, booking.seats, user_id=request.user.id)
        
        if 'seat_reservation' in request.session:
            reservation = request.session['seat_reservation']
            if str(showtime_id) in reservation:
                del reservation[str(showtime_id)]
                request.session['seat_reservation'] = reservation
        
        logger.info(
            f"Booking {booking.booking_number} marked as FAILED by user {request.user.id}. "
            f"Reason: {reason}. Seats released: {booking.seats}"
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Booking cancelled and seats released',
            'booking_id': booking.id,
            'seats_released': booking.seats
        })
        
    except Exception as e:
        logger.error(f"Error cancelling booking {booking_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to cancel booking. Please try again.'
        }, status=500)

@csrf_exempt
def release_booking_beacon(request, booking_id):

    if request.method != 'POST':
        return HttpResponse(status=405)
    
    try:
        from django.db import transaction
        
        data = json.loads(request.body) if request.body else {}
        reason = data.get('reason', 'Tab closed (beacon)')
        
        with transaction.atomic():
            if supports_select_for_update():
                booking = Booking.objects.select_for_update().filter(
                    id=booking_id, 
                    status='PENDING'
                ).first()
            else:
                booking = Booking.objects.filter(
                    id=booking_id, 
                    status='PENDING'
                ).first()
            
            if not booking:
                return HttpResponse(status=200)
            
            if booking.payment_received_at:
                logger.info(
                    f"BEACON IGNORED: Booking {booking.booking_number} already has payment_received_at. "
                    f"Payment confirmation is in progress - not sending failure email."
                )
                return HttpResponse(status=200)
            
            booking.status = 'FAILED'
            booking.save()
        
        
        SeatManager.release_seats(booking.showtime.id, booking.seats, user_id=booking.user.id)
        
        logger.info(
            f"BEACON: Booking {booking.booking_number} released. "
            f"Reason: {reason}. Seats: {booking.seats}"
        )
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Beacon release error for booking {booking_id}: {e}")
        return HttpResponse(status=200)  # Return 200 anyway - beacon can't retry

