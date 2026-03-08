from django.http import JsonResponse
from django.contrib.auth.models import User
from accounts.models import UserProfile
from django.utils import timezone
import os

def make_admin_temp(request):
    if not os.environ.get('DEBUG') == 'True' and request.META.get('REMOTE_ADDR') != '127.0.0.1':
        return JsonResponse({'error': 'Not allowed'}, status=403)
    
    username = request.GET.get('username', 'biku23sdcxsaiml')
    
    try:
        user = User.objects.get(username=username)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()
        
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.is_email_verified = True
        profile.email_verified_at = timezone.now()
        profile.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{username} is now admin',
            'user': {
                'username': user.username,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'email_verified': profile.is_email_verified
            }
        })
    except User.DoesNotExist:
        return JsonResponse({'error': f'User {username} not found'}, status=404)
