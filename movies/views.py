from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView
from .models import Movie, Genre, Language
from .theater_models import City, Showtime
from django.db.models import Q
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
import json
from embed_video.backends import detect_backend
from django.core.cache import cache

def movie_list(request):

    movies = Movie.objects.filter(is_active=True).order_by('-release_date')
    
    query = request.GET.get('q', '') # General search query
    selected_genre = request.GET.get('genre', '')
    selected_language = request.GET.get('language', '')
    
    if query:
        movies = movies.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(director__icontains=query) |
            Q(cast__icontains=query)
        )
    
    if selected_genre:
        movies = movies.filter(genres__slug=selected_genre)
    
    if selected_language:
        movies = movies.filter(language__code=selected_language)
    

    context = {
        'movies': movies,
        'genres': Genre.objects.all(),
        'languages': Language.objects.all(),
        'selected_genre': request.GET.get('genre', ''),
        'selected_language': request.GET.get('language', ''),
        'query': query,
    }
    
    return render(request, 'movies/movie_list.html', context)

def movie_detail(request, slug):

    movie = get_object_or_404(Movie, slug=slug, is_active=True)
    
    showtimes = Showtime.objects.filter(
        movie=movie,
        is_active=True
    ).order_by('date', 'start_time')
    
    cities_with_showtimes = []
    cities = City.objects.filter(is_active=True)
    
    for city in cities:
        city_showtimes = showtimes.filter(screen__theater__city=city)
        
        if city_showtimes.exists():
            theaters = {}
            for showtime in city_showtimes:
                theater = showtime.screen.theater
                if theater.id not in theaters:
                    theaters[theater.id] = {
                        'theater': theater,
                        'showtimes': []
                    }
                theaters[theater.id]['showtimes'].append(showtime)
            
            cities_with_showtimes.append({
                'city': city,
                'theaters': list(theaters.values())
            })
    
    user_review = None

    reviews = []

    recommended_movies = Movie.objects.filter(
        genres__in=movie.genres.all(),
        is_active=True
    ).exclude(id=movie.id).distinct()[:4]

    recently_added = Movie.objects.filter(is_active=True).order_by('-created_at').exclude(id=movie.id)[:4]

    context = {
        'movie': movie,
        'cities_with_showtimes': cities_with_showtimes,
        'genres': movie.genres.all(),
        'recommended_movies': recommended_movies,
        'recently_added': recently_added,
    }
    
    return render(request, 'movies/movie_detail.html', context)

def home(request):

    featured_movies = Movie.objects.filter(is_active=True).order_by('-release_date')[:6]
    
    from datetime import date, timedelta
    next_week = date.today() + timedelta(days=7)
    
    upcoming_showtimes = Showtime.objects.filter(
        date__range=[date.today(), next_week],
        is_active=True
    ).values_list('movie_id', flat=True).distinct()
    
    now_showing = Movie.objects.filter(
        id__in=upcoming_showtimes,
        is_active=True
    )[:8]
    
    genres = Genre.objects.all()[:10]
    
    
    context = {
        'featured_movies': featured_movies,
        'now_showing': now_showing,
        'genres': genres,
    }
    
    return render(request, 'movies/home.html', context)

def movie_trailer(request, slug):

    movie = get_object_or_404(Movie, slug=slug, is_active=True)
    
    trailer = None
    if movie.trailer_url:
        backend = detect_backend(movie.trailer_url)
        trailer = {
            'url': movie.trailer_url,
            'backend': backend,
            'youtube_id': movie.youtube_id,
        }
    
    showtimes = Showtime.objects.filter(
        movie=movie,
        is_active=True,
        date__gte=timezone.now().date()
    ).order_by('date', 'start_time')[:10]
    
    
    
    
    context = {
        'movie': movie,
        'trailer': trailer,
        'showtimes': showtimes,
        'genres': movie.genres.all(),
    }
    
    return render(request, 'movies/movie_trailer.html', context)

def movie_autocomplete(request):

    query = request.GET.get('q', '')
    
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    cache_key = f'autocomplete_{query.lower()}'
    results = cache.get(cache_key)
    
    if not results:
        movies = Movie.objects.filter(
            Q(title__icontains=query) |
            Q(cast__icontains=query) |
            Q(director__icontains=query),
            is_active=True
        )[:10]
        
        results = [
            {
                'id': movie.id,
                'title': movie.title,
                'year': movie.release_date.year,
                'rating': movie.rating,
                'poster_url': movie.poster.url if movie.poster else '',
                'url': movie.get_absolute_url(),
            }
            for movie in movies
        ]
        
        cache.set(cache_key, results, timeout=300)  # Cache for 5 minutes
    
    return JsonResponse({'results': results})

def search_youtube_trailer(request, movie_id):

    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    movie = get_object_or_404(Movie, id=movie_id)
    
    import requests
    
    search_query = f"{movie.title} {movie.release_date.year} official trailer"
    api_key = settings.YOUTUBE_API_KEY
    
    if not api_key:
        return JsonResponse({'error': 'YouTube API key not configured'})
    
    try:
        url = f"https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'q': search_query,
            'key': api_key,
            'maxResults': 5,
            'type': 'video',
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        videos = []
        for item in data.get('items', []):
            video_id = item['id']['videoId']
            title = item['snippet']['title']
            thumbnail = item['snippet']['thumbnails']['high']['url']
            
            videos.append({
                'video_id': video_id,
                'title': title,
                'thumbnail': thumbnail,
                'url': f'https://www.youtube.com/watch?v={video_id}',
            })
        
        return JsonResponse({'videos': videos})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)