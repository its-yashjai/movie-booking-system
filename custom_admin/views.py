

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from datetime import timedelta
from bookings.models import Booking
from movies.models import Movie
from movies.theater_models import Theater

def admin_login(request):

    if request.user.is_authenticated and request.user.is_staff:
        return redirect('custom_admin:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('custom_admin:dashboard')
        else:
            return render(request, 'custom_admin/login.html', {
                'error': 'Invalid credentials or not a staff member'
            })
    
    return render(request, 'custom_admin/login.html')

@login_required(login_url='custom_admin:login')
def admin_logout(request):

    if request.user.is_staff:
        logout(request)
    return redirect('custom_admin:login')

@staff_member_required(login_url='custom_admin:login')
def dashboard(request):

    from datetime import datetime, timedelta
    
    today = timezone.now().date()
    
    movie_id = request.GET.get('movie_id')
    theater_id = request.GET.get('theater_id')
    period = request.GET.get('period', 'all')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    filters = Q(status='CONFIRMED')
    
    if movie_id:
        filters &= Q(showtime__movie_id=movie_id)
    
    if theater_id:
        filters &= Q(showtime__screen__theater_id=theater_id)
    
    period_filters = Q()
    if date_from and date_to:
        period_filters = Q(created_at__date__gte=date_from, created_at__date__lte=date_to)
    elif period == 'today':
        period_filters = Q(created_at__date=today)
    elif period == 'week':
        week_ago = today - timedelta(days=7)
        period_filters = Q(created_at__date__gte=week_ago)
    elif period == 'month':
        month_ago = today - timedelta(days=30)
        period_filters = Q(created_at__date__gte=month_ago)
    
    final_filters = filters & period_filters if period_filters else filters
    
    filtered_bookings = Booking.objects.filter(final_filters)
    
    total_revenue = Booking.objects.filter(filters).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    period_revenue = filtered_bookings.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_bookings = Booking.objects.filter(filters).count()
    period_bookings = filtered_bookings.count()
    
    end_date = today
    start_date = today - timedelta(days=29)
    revenue_data = []
    current_date = start_date
    
    while current_date <= end_date:
        daily_bookings = Booking.objects.filter(
            filters,
            created_at__date=current_date
        )
        daily_revenue = daily_bookings.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        revenue_data.append({
            'date': current_date.strftime('%b %d'),
            'revenue': float(daily_revenue)
        })
        current_date += timedelta(days=1)
    
    top_movies = Movie.objects.filter(
        showtime__booking__in=filtered_bookings
    ).annotate(
        booking_count=Count('showtime__booking', filter=Q(showtime__booking__in=filtered_bookings))
    ).distinct().order_by('-booking_count')[:5]
    
    top_theaters = Theater.objects.filter(
        screen__showtime__booking__in=filtered_bookings
    ).annotate(
        booking_count=Count('screen__showtime__booking', filter=Q(screen__showtime__booking__in=filtered_bookings)),
        revenue=Sum('screen__showtime__booking__total_amount', filter=Q(screen__showtime__booking__in=filtered_bookings))
    ).distinct().order_by('-revenue')[:5]
    
    recent_bookings = filtered_bookings.select_related(
        'user', 'showtime__movie'
    ).order_by('-created_at')[:5]
    
    all_movies = Movie.objects.filter(is_active=True).order_by('title')
    all_theaters = Theater.objects.order_by('name')
    
    context = {
        'total_revenue': total_revenue,
        'period_revenue': period_revenue,
        'total_bookings': total_bookings,
        'period_bookings': period_bookings,
        
        'revenue_data': revenue_data,
        'top_movies': top_movies,
        'top_theaters': top_theaters,
        
        'recent_bookings': recent_bookings,
        
        'all_movies': all_movies,
        'all_theaters': all_theaters,
        'selected_movie_id': movie_id,
        'selected_theater_id': theater_id,
        'selected_period': period,
        'date_from': date_from,
        'date_to': date_to,
        
        'period_label': {
            'today': 'Today',
            'week': 'Last 7 Days',
            'month': 'Last 30 Days',
            'all': 'All Time'
        }.get(period, 'Custom Range' if date_from and date_to else 'All Time'),
    }
    
    return render(request, 'custom_admin/dashboard_server.html', context)

def debug_page(request):

    return render(request, 'custom_admin/debug.html')

@staff_member_required(login_url='custom_admin:login')
@require_http_methods(["GET"])
def api_stats(request):

    today = timezone.now().date()
    
    filters = Q(status='CONFIRMED')
    
    movie_id = request.GET.get('movie_id')
    if movie_id:
        filters &= Q(showtime__movie_id=movie_id)
    
    theater_id = request.GET.get('theater_id')
    if theater_id:
        filters &= Q(showtime__screen__theater_id=theater_id)
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    period = request.GET.get('period', 'all')
    period_filters = Q()
    
    if date_from and date_to:
        period_filters = Q(created_at__date__gte=date_from, created_at__date__lte=date_to)
    elif period == 'today':
        period_filters = Q(created_at__date=today)
    elif period == 'week':
        week_ago = today - timedelta(days=7)
        period_filters = Q(created_at__date__gte=week_ago)
    elif period == 'month':
        month_ago = today - timedelta(days=30)
        period_filters = Q(created_at__date__gte=month_ago)
    
    total_revenue = Booking.objects.filter(
        filters
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    period_revenue = Booking.objects.filter(
        filters & period_filters
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    total_bookings = Booking.objects.filter(filters).count()
    
    period_bookings = Booking.objects.filter(
        filters & period_filters
    ).count()
    
    return JsonResponse({
        'total_revenue': float(total_revenue),
        'today_revenue': float(period_revenue),
        'total_bookings': total_bookings,
        'today_bookings': period_bookings,
    })

@staff_member_required(login_url='custom_admin:login')
@require_http_methods(["GET"])
def api_revenue(request):

    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    filters = Q(status='CONFIRMED')
    
    movie_id = request.GET.get('movie_id')
    if movie_id:
        filters &= Q(showtime__movie_id=movie_id)
    
    theater_id = request.GET.get('theater_id')
    if theater_id:
        filters &= Q(showtime__screen__theater_id=theater_id)
    
    dates = []
    revenues = []
    
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime('%Y-%m-%d'))
        
        daily_revenue = Booking.objects.filter(
            created_at__date=current_date,
            **{'__'.join(str(k).split('__')[:-1]) if '__' in k else k: v for k, v in filters.children}
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        daily_revenue = Booking.objects.filter(
            filters,
            created_at__date=current_date
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        revenues.append(float(daily_revenue))
        current_date += timedelta(days=1)
    
    return JsonResponse({
        'dates': dates,
        'revenues': revenues,
    })

@staff_member_required(login_url='custom_admin:login')
@require_http_methods(["GET"])
def api_bookings(request):

    filters = Q(status='CONFIRMED')
    
    movie_id = request.GET.get('movie_id')
    if movie_id:
        filters &= Q(showtime__movie_id=movie_id)
    
    theater_id = request.GET.get('theater_id')
    if theater_id:
        filters &= Q(showtime__screen__theater_id=theater_id)
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    period = request.GET.get('period', 'all')
    period_filters = Q()
    today = timezone.now().date()
    
    if date_from and date_to:
        period_filters = Q(created_at__date__gte=date_from, created_at__date__lte=date_to)
    elif period == 'today':
        period_filters = Q(created_at__date=today)
    elif period == 'week':
        week_ago = today - timedelta(days=7)
        period_filters = Q(created_at__date__gte=week_ago)
    elif period == 'month':
        month_ago = today - timedelta(days=30)
        period_filters = Q(created_at__date__gte=month_ago)
    
    final_filters = filters & period_filters if period_filters else filters
    
    filtered_bookings = Booking.objects.filter(final_filters)
    
    movies = Movie.objects.filter(
        showtime__booking__in=filtered_bookings
    ).annotate(
        booking_count=Count('showtime__booking', filter=Q(showtime__booking__in=filtered_bookings))
    ).distinct().order_by('-booking_count')[:5]
    
    movie_data = [
        {
            'title': m.title,
            'bookings': m.booking_count,
        }
        for m in movies
    ]
    
    recent = Booking.objects.filter(
        final_filters
    ).select_related('user', 'showtime__movie').order_by('-created_at')[:5]
    
    booking_data = [
        {
            'user': b.user.username,
            'movie': b.showtime.movie.title,
            'amount': float(b.total_amount),
            'date': b.created_at.strftime('%Y-%m-%d %H:%M'),
        }
        for b in recent
    ]
    
    return JsonResponse({
        'movies': movie_data,
        'bookings': booking_data,
    })

@staff_member_required(login_url='custom_admin:login')
@require_http_methods(["GET"])
def api_theaters(request):

    booking_filters = Q(status='CONFIRMED')
    
    movie_id = request.GET.get('movie_id')
    if movie_id:
        booking_filters &= Q(showtime__movie_id=movie_id)
    
    theater_id = request.GET.get('theater_id')
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    period = request.GET.get('period', 'all')
    period_filters = Q()
    today = timezone.now().date()
    
    if date_from and date_to:
        period_filters = Q(created_at__date__gte=date_from, created_at__date__lte=date_to)
    elif period == 'today':
        period_filters = Q(created_at__date=today)
    elif period == 'week':
        week_ago = today - timedelta(days=7)
        period_filters = Q(created_at__date__gte=week_ago)
    elif period == 'month':
        month_ago = today - timedelta(days=30)
        period_filters = Q(created_at__date__gte=month_ago)
    
    final_booking_filters = booking_filters & period_filters if period_filters else booking_filters
    
    filtered_bookings = Booking.objects.filter(final_booking_filters)
    
    query = Theater.objects.filter(
        screen__showtime__booking__in=filtered_bookings
    ).annotate(
        booking_count=Count('screen__showtime__booking', filter=Q(screen__showtime__booking__in=filtered_bookings)),
        revenue=Sum('screen__showtime__booking__total_amount', filter=Q(screen__showtime__booking__in=filtered_bookings))
    ).distinct().order_by('-revenue')[:5]
    
    if theater_id:
        query = query.filter(id=theater_id)
    
    theater_data = [
        {
            'name': t.name,
            'bookings': t.booking_count or 0,
            'revenue': float(t.revenue or 0),
        }
        for t in query
    ]
    
    return JsonResponse({
        'theaters': theater_data,
    })

@staff_member_required(login_url='custom_admin:login')
def movie_management(request):

    return render(request, 'custom_admin/movie_management.html')

@staff_member_required(login_url='custom_admin:login')
@require_http_methods(["GET"])
def api_filter_options(request):

    movies = Movie.objects.filter(is_active=True).values('id', 'title').order_by('title')
    theaters = Theater.objects.values('id', 'name').order_by('name')
    
    return JsonResponse({
        'movies': list(movies),
        'theaters': list(theaters),
    })

@staff_member_required(login_url='custom_admin:login')
@require_http_methods(["GET"])
def api_dashboard_filtered(request):

    date_from_str = request.GET.get('date_from')
    date_to_str = request.GET.get('date_to')
    movie_id = request.GET.get('movie')
    theater_id = request.GET.get('theater')
    
    bookings_qs = Booking.objects.filter(status='CONFIRMED')
    
    if date_from_str:
        bookings_qs = bookings_qs.filter(created_at__date__gte=date_from_str)
    
    if date_to_str:
        bookings_qs = bookings_qs.filter(created_at__date__lte=date_to_str)
    
    if movie_id:
        bookings_qs = bookings_qs.filter(showtime__movie_id=movie_id)
    
    if theater_id:
        bookings_qs = bookings_qs.filter(showtime__screen__theater_id=theater_id)
    
    total_revenue = bookings_qs.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_bookings = bookings_qs.count()
    
    today = timezone.now().date()
    today_revenue = bookings_qs.filter(created_at__date=today).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    today_bookings = bookings_qs.filter(created_at__date=today).count()
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    dates = []
    revenues = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime('%Y-%m-%d'))
        daily_revenue = bookings_qs.filter(
            created_at__date=current_date
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        revenues.append(float(daily_revenue))
        current_date += timedelta(days=1)
    
    top_movies = Movie.objects.filter(
        showtime__booking__in=bookings_qs
    ).annotate(
        booking_count=Count('showtime__booking', filter=Q(showtime__booking__in=bookings_qs))
    ).order_by('-booking_count')[:5]
    
    movies_data = [
        {'title': m.title, 'bookings': m.booking_count}
        for m in top_movies
    ]
    
    top_theaters = Theater.objects.filter(
        screen__showtime__booking__in=bookings_qs
    ).annotate(
        booking_count=Count('screen__showtime__booking', filter=Q(screen__showtime__booking__in=bookings_qs)),
        revenue=Sum('screen__showtime__booking__total_amount', filter=Q(screen__showtime__booking__in=bookings_qs))
    ).order_by('-revenue')[:5]
    
    theaters_data = [
        {'name': t.name, 'bookings': t.booking_count or 0, 'revenue': float(t.revenue or 0)}
        for t in top_theaters
    ]
    
    recent_bookings_qs = bookings_qs.select_related('user', 'showtime__movie').order_by('-created_at')[:5]
    
    bookings_data = [
        {
            'user': b.user.username,
            'movie': b.showtime.movie.title,
            'amount': float(b.total_amount),
            'date': b.created_at.strftime('%Y-%m-%d %H:%M'),
        }
        for b in recent_bookings_qs
    ]
    
    return JsonResponse({
        'total_revenue': float(total_revenue),
        'today_revenue': float(today_revenue),
        'total_bookings': total_bookings,
        'today_bookings': today_bookings,
        'revenue_data': {'dates': dates, 'revenues': revenues},
        'top_movies': movies_data,
        'top_theaters': theaters_data,
        'recent_bookings': bookings_data,
    })
