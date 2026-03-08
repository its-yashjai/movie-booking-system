from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random
import string

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    
    email_otp = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    otp_attempts = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts_userprofile'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def generate_otp(self):
        self.email_otp = ''.join(random.choices(string.digits, k=6))
        self.otp_created_at = timezone.now()
        self.otp_attempts = 0
        self.save()
        return self.email_otp
    
    def is_otp_valid(self, otp):
        if not self.email_otp or not self.otp_created_at:
            return False
        
        if self.email_otp != otp:
            self.otp_attempts += 1
            self.save()
            return False
        
        time_elapsed = (timezone.now() - self.otp_created_at).total_seconds()
        if time_elapsed > 300:
            return False
        
        return True
    
    def mark_email_verified(self):
        self.is_email_verified = True
        self.email_verified_at = timezone.now()
        self.email_otp = None
        self.otp_created_at = None
        self.otp_attempts = 0
        self.save()
