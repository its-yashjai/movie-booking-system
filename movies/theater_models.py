from django.db import models
from django.utils.text import slugify
from django.core.validators import MaxValueValidator, MinValueValidator

class City(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'cities'
        ordering = ['name']

class Theater(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    
    address = models.TextField()
    contact_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    has_parking = models.BooleanField(default=False)
    has_food_court = models.BooleanField(default=False)
    has_wheelchair_access = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}, {self.city.name}"

    class Meta:
        ordering = ['city', 'name']

class Screen(models.Model):
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)  # Screen 1, Screen 2, etc.
    
    screen_type = models.CharField(max_length=20, choices=[
        ('2D', '2D'),
        ('3D', '3D'),
        ('IMAX', 'IMAX'),
        ('4DX', '4DX'),
    ], default='2D')
    
    total_seats = models.IntegerField(default=100)
    
    def __str__(self):
        return f"{self.theater.name} ({self.theater.city.name}) - {self.name} [{self.screen_type}]"
    
    class Meta:
        ordering = ['theater', 'name']

class Showtime(models.Model):
    movie = models.ForeignKey('movies.Movie', on_delete=models.CASCADE)
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE)
    
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    price = models.DecimalField(max_digits=8, decimal_places=2, default=200.00)
    
    available_seats = models.IntegerField(
        default=100,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.movie.title} - {self.date} {self.start_time}"
    
    def get_formatted_time(self):

        return self.start_time.strftime("%I:%M %p")
    
    def get_formatted_date(self):

        return self.date.strftime("%d %b, %Y")
    
    class Meta:
        ordering = ['date', 'start_time']