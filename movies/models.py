from django.db import models
from django.utils.text import slugify

from embed_video.fields import EmbedVideoField
class Genre(models.Model):

    name = models.CharField(max_length=100)
    
    slug = models.SlugField(max_length=100, unique=True)
    
    icon = models.CharField(max_length=50, default="fas fa-film")
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class Language(models.Model):

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)  # ISO code like 'hi', 'en'
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class Movie(models.Model):

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    
    description = models.TextField()
    duration = models.IntegerField(help_text="Duration in minutes")
    release_date = models.DateField()
    
    certificate = models.CharField(max_length=10, choices=[
        ('U', 'U - Universal'),
        ('UA', 'UA - Parental Guidance'),
        ('A', 'A - Adults Only'),
        ('R', 'R - Restricted'),
    ], default='UA')
    
    status = models.CharField(max_length=20, choices=[
        ('now_showing', 'Now Showing'),
        ('coming_soon', 'Coming Soon'),
        ('expired', 'Expired'),
    ], default='now_showing')

    rating = models.FloatField(default=0.0)  # IMDb style rating
    
    poster = models.ImageField(upload_to='movie_posters/', blank=True, null=True)
    
    trailer_url = models.URLField(blank=True)  # YouTube URL
    
    genres = models.ManyToManyField(Genre, related_name='movies')
    
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True, related_name='movies')
    
    director = models.CharField(max_length=200, blank=True)
    
    cast = models.TextField(blank=True, help_text="Comma separated list of actors")
    
    is_active = models.BooleanField(default=True)  # Soft delete logic: hide instead of delete
    created_at = models.DateTimeField(auto_now_add=True)  # Set once on creation
    updated_at = models.DateTimeField(auto_now=True)      # Updated every time save() is called
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.title} ({self.release_date.year})"
    
    def duration_formatted(self):

        hours = self.duration // 60
        minutes = self.duration % 60
        return f"{hours}h {minutes}m"
    
    def get_genres_list(self):

        return ", ".join([genre.name for genre in self.genres.all()])

    rating_count = models.IntegerField(default=0)
    total_rating = models.FloatField(default=0.0)

    @property
    def youtube_id(self):
        import re
        pattern = r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})'
        match = re.search(pattern, self.trailer_url)
        if match:
            return match.group(1)
        return None 

    def update_rating(self, new_rating):
        self.total_rating += new_rating
        self.rating_count += 1
        self.rating = self.total_rating / self.rating_count
        self.save()

    def get_average_rating(self):

        if self.rating_count > 0:
            return round(self.total_rating / self.rating_count, 1)
        return 0.0
    def get_rating_percentage(self):

        return (self.rating / 10) * 100 if self.rating else 0

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('movie_detail', kwargs={'slug': self.slug})

    class Meta:
        ordering = ['-release_date', 'title']