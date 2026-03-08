from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q


class EmailBackend(ModelBackend):
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get('email')
        
        if username is None or password is None:
            return None
        
        try:
            user = User.objects.filter(
                Q(email__iexact=username) | Q(username__iexact=username)
            ).order_by('-date_joined').first()
            
            if user is None:
                User().set_password(password)
                return None
            
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
            
            return None
        except Exception:
            return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
