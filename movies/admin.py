from django.contrib import admin
from .models import Movie, Genre, Language
from .theater_models import City, Theater, Screen, Showtime
from django.utils.html import format_html

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon']
    
    prepopulated_fields = {'slug': ('name',)}
    
    search_fields = ['name']

@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']
    search_fields = ['name', 'code']

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['title', 'release_date', 'rating', 'duration_formatted', 'is_active', 'poster_preview']
    
    list_filter = ['genres', 'language', 'is_active', 'release_date']
    
    search_fields = ['title', 'director', 'cast']
    
    prepopulated_fields = {'slug': ('title',)}
    
    filter_horizontal = ['genres']
    
    fieldsets = [
        ('Basic Info', {
            'fields': ['title', 'slug', 'description', 'poster', 'trailer_url']
        }),
        ('Details', {
            'fields': ['release_date', 'duration', 'certificate', 'rating', 'genres', 'language']
        }),
        ('Cast & Crew', {
            'fields': ['director', 'cast']
        }),
        ('Status', {
            'fields': ['is_active']
        }),
    ]
    
    class Media:
        css = {
            'all': ('admin/css/movie_admin.css',)
        }
    
    def duration_formatted(self, obj):
        return obj.duration_formatted()
    duration_formatted.short_description = 'Duration'  # Sets the column header name
    
    def poster_preview(self, obj):
        if obj.poster:
            return format_html(
                '<img src="{}" style="width: 50px; height: 75px; object-fit: cover; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />', 
                obj.poster.url
            )
        return format_html('<div style="width: 50px; height: 75px; background: #f0f0f0; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #999;">{}</div>', 'No Poster')
    poster_preview.short_description = 'Poster'

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ['is_active']

@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'has_parking', 'has_food_court', 'is_active']
    list_filter = ['city', 'is_active', 'has_parking', 'has_food_court']
    search_fields = ['name', 'address']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ['name', 'theater', 'screen_type', 'total_seats']
    list_filter = ['theater', 'screen_type']
    
    search_fields = ['name', 'theater__name']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "theater":
            kwargs["queryset"] = Theater.objects.select_related('city').all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Showtime)
class ShowtimeAdmin(admin.ModelAdmin):
    list_display = ['movie', 'screen', 'date', 'start_time', 'price', 'available_seats', 'is_active']
    list_filter = ['date', 'is_active', 'screen__theater__city']
    
    search_fields = ['movie__title', 'screen__name']
    
    date_hierarchy = 'date'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "screen":
            kwargs["queryset"] = Screen.objects.select_related('theater__city').all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)