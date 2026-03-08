from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    
    path('movies/', views.movie_list, name='movie_list'),

    
    path('movies/<slug:slug>/', views.movie_detail, name='movie_detail'),
    
    path('movie/<slug:slug>/trailer/', views.movie_trailer, name='movie_trailer'),
    
    
    
    path('autocomplete/', views.movie_autocomplete, name='movie_autocomplete'),
    
    path('movie/<int:movie_id>/youtube-search/', views.search_youtube_trailer, name='search_youtube_trailer'),
]