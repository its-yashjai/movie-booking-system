from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
    
    path('', views.dashboard, name='dashboard'),
    path('movies/', views.movie_management, name='movie_management'),
    path('debug/', views.debug_page, name='debug_page'),
    
    path('api/stats/', views.api_stats, name='api_stats'),
    path('api/revenue/', views.api_revenue, name='api_revenue'),
    path('api/bookings/', views.api_bookings, name='api_bookings'),
    path('api/theaters/', views.api_theaters, name='api_theaters'),
    path('api/filter-options/', views.api_filter_options, name='api_filter_options'),
    path('api/dashboard-filtered/', views.api_dashboard_filtered, name='api_dashboard_filtered'),
]
