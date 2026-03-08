from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


def email_verified_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        if not hasattr(request.user, 'profile'):
            messages.error(request, '⚠️ Please complete your profile setup.')
            return redirect('verify_otp')
        
        if not request.user.profile.is_email_verified:
            messages.warning(
                request,
                '📧 Please verify your email address to access this feature. '
                'Check your inbox for the verification code.'
            )
            return redirect('verify_otp')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper
