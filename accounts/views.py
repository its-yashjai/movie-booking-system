from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .forms import CustomUserCreationForm
from .models import UserProfile
from .email_utils import AuthEmailService
import json
import logging

logger = logging.getLogger(__name__)

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                email = form.cleaned_data.get('email')
                
                if User.objects.filter(email=email).exists():
                    messages.error(request, 
                        f'❌ An account with email "{email}" already exists. Please use a different email or try logging in.')
                    return render(request, 'registration/register.html', {'form': form})
                
                user = form.save(commit=False)
                user.is_active = False
                user.email = email
                user.save()
                
                profile, created = UserProfile.objects.get_or_create(user=user)
                logger.info(f"User registration started for: {user.email}")
                
                otp = profile.generate_otp()
                
                try:
                    email_sent = AuthEmailService.send_email_verification_email(user)
                    if email_sent:
                        messages.success(request, 
                            f'🎉 Account created successfully! A 6-digit verification code has been sent to {user.email}. Please check your inbox (and spam folder) and enter the code on the next page.')
                        logger.info(f"Verification email sent to: {user.email}")
                    else:
                        messages.warning(request, 
                            '⚠️ Account created, but we had trouble sending the verification email. You can try resending it on the next page.')
                        logger.warning(f"Failed to send verification email to: {user.email}")
                except Exception as e:
                    logger.error(f"Failed to send verification email to {user.email}: {e}")
                    messages.warning(request, 
                        '⚠️ Account created, but we had trouble sending the verification email. You can try resending it on the next page.')
                
                request.session['pending_user_id'] = user.id
                return redirect('verify_otp')
                
            except Exception as e:
                logger.error(f"Registration error for {form.cleaned_data.get('email', 'unknown')}: {e}")
                if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                    messages.error(request, 
                        '❌ This email or username is already taken. Please use a different one or try logging in.')
                else:
                    messages.error(request, 
                        '❌ Registration failed due to a system error. Please try again or contact support if the problem persists.')
        else:
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        error_messages.append(f"❌ {error}")
                    elif field == 'email':
                        if 'already exists' in str(error).lower() or 'taken' in str(error).lower():
                            error_messages.append(f"❌ This email is already registered. Please login or use a different email.")
                        else:
                            error_messages.append(f"❌ Email: {error}")
                    elif field == 'username':
                        if 'already exists' in str(error).lower() or 'taken' in str(error).lower():
                            error_messages.append(f"❌ This username is already taken. Please choose a different one.")
                        else:
                            error_messages.append(f"❌ Username: {error}")
                    else:
                        field_name = field.replace('_', ' ').title()
                        error_messages.append(f"❌ {field_name}: {error}")
            
            if error_messages:
                for msg in error_messages:
                    messages.error(request, msg)
            else:
                messages.error(request, '❌ Please correct the errors in the form and try again.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')
        
        if not email or not password:
            messages.error(request, '❌ Please enter both email and password.')
            return render(request, 'registration/login.html')
        
        try:
            user_exists = User.objects.filter(email=email).exists()
            if not user_exists:
                messages.error(request, 
                    f'❌ No account found with email "{email}". Please check your email or sign up for a new account.')
                return render(request, 'registration/login.html')
        except Exception as e:
            logger.error(f"Error checking user existence: {e}")
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            if not user.is_active:
                messages.error(request, 
                    '❌ Your account is not activated. Please check your email for the verification code.')
                return render(request, 'registration/login.html')
            
            if not user.is_superuser and not user.is_staff:
                try:
                    profile = user.profile
                    if not profile.is_email_verified:
                        messages.warning(request, 
                            '📧 Please verify your email address before logging in. Check your inbox for the verification code.')
                        request.session['pending_user_id'] = user.id
                        return redirect('verify_otp')
                except UserProfile.DoesNotExist:
                    UserProfile.objects.create(user=user, is_email_verified=True)
                    logger.info(f"Created profile for existing user: {user.username}")
            else:
                try:
                    profile = user.profile
                    if not profile.is_email_verified:
                        profile.is_email_verified = True
                        profile.save()
                        logger.info(f"Auto-verified email for admin/staff: {user.username}")
                except UserProfile.DoesNotExist:
                    UserProfile.objects.create(user=user, is_email_verified=True)
                    logger.info(f"Created verified profile for admin/staff: {user.username}")
            
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            welcome_name = user.first_name or user.username
            messages.success(request, 
                f'🎉 Welcome back, {welcome_name}! You have been logged in successfully.')
            
            next_page = request.GET.get('next', 'home')
            logger.info(f"User {user.username} logged in successfully")
            return redirect(next_page)
        else:
            messages.error(request, 
                '❌ Incorrect password. Please try again or use "Forgot Password" to reset it.')
    
    return render(request, 'registration/login.html')

def logout_view(request):
    username = request.user.username if request.user.is_authenticated else "User"
    logout(request)
    messages.success(request, f'Goodbye {username}! You have been logged out successfully.')
    return redirect('home')

def verify_otp(request):
    user_id = request.session.get('pending_user_id')
    if not user_id:
        messages.error(request, 'No pending verification found.')
        return redirect('register')
    
    try:
        user = User.objects.get(id=user_id)
        profile = user.profile
    except (User.DoesNotExist, UserProfile.DoesNotExist):
        messages.error(request, 'Invalid verification session.')
        return redirect('register')
    
    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        
        if profile.is_otp_valid(otp):
            profile.is_email_verified = True
            profile.email_verified_at = timezone.now()
            profile.email_otp = None
            profile.save()
            
            user.is_active = True
            user.save()
            
            del request.session['pending_user_id']
            
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            
            try:
                AuthEmailService.send_welcome_email(user)
            except Exception as e:
                logger.error(f"Failed to send welcome email: {e}")
            
            messages.success(request, 
                f'Email verified successfully! Welcome to BookMyshowClone, {user.username}!')
            return redirect('verification_success')
        else:
            messages.error(request, 'Invalid or expired OTP. Please try again.')
            
            if profile.otp_attempts >= 3:
                messages.error(request, 
                    'Too many failed attempts. Please request a new verification code.')
                return redirect('resend_verification')
    
    context = {
        'pending_user': user,
        'otp_attempts': profile.otp_attempts,
    }
    return render(request, 'accounts/verify_otp.html', context)

def verification_pending(request):
    return render(request, 'accounts/verification_pending.html')

def verification_success(request):
    return render(request, 'accounts/verification_success.html')

def resend_verification_email(request):
    user_id = request.session.get('pending_user_id')
    if not user_id:
        messages.error(request, 'No pending verification found.')
        return redirect('register')
    
    try:
        user = User.objects.get(id=user_id)
        profile = user.profile
        
        otp = profile.generate_otp()
        
        email_sent = AuthEmailService.send_email_verification_email(user)
        if email_sent:
            messages.success(request, 
                f'📧 New verification code sent to {user.email}. Please check your inbox and enter the 6-digit code.')
        else:
            messages.error(request, 'Failed to send verification email. Please try again.')
        
    except Exception as e:
        logger.error(f"Failed to resend verification email: {e}")
        messages.error(request, 'Failed to send verification email. Please try again.')
    
    return redirect('verify_otp')

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, '❌ Please enter your email address.')
            return render(request, 'accounts/forgot_password.html')
        
        try:
            user = User.objects.get(email=email)
            
            if not user.is_active:
                messages.error(request, 
                    f'❌ Account with {email} is deactivated. Please contact support.')
                logger.warning(f"Password reset attempted for inactive user: {email}")
                return redirect('login')
            
            profile, created = UserProfile.objects.get_or_create(user=user)
            otp = profile.generate_otp()
            
            email_sent = AuthEmailService.send_password_reset_otp(user, otp)
            
            if email_sent:
                request.session['reset_email'] = email
                messages.success(request, 
                    f'✅ Password reset code has been sent to {email}. Please check your inbox. Code expires in 5 minutes.')
                logger.info(f"Password reset OTP sent to: {email}")
                return redirect('verify_password_reset_otp')
            else:
                messages.error(request, 
                    '❌ Failed to send password reset code. Please try again or contact support.')
                logger.error(f"Failed to send password reset OTP to: {email}")
                
            return redirect('forgot_password')
            
        except User.DoesNotExist:
            messages.error(request, 
                f'❌ No account found with email {email}. Please check the email address or sign up for a new account.')
            logger.info(f"Password reset attempted for non-existent email: {email}")
            return redirect('forgot_password')
            
        except Exception as e:
            logger.error(f"Password reset error for {email}: {e}")
            messages.error(request, 
                '❌ Failed to send password reset code due to a system error. Please try again.')
    
    return render(request, 'accounts/forgot_password.html')

def verify_password_reset_otp(request):
    reset_email = request.session.get('reset_email')
    
    if not reset_email:
        messages.error(request, '❌ Invalid password reset session. Please start again.')
        return redirect('forgot_password')
    
    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        
        if not otp:
            messages.error(request, '❌ Please enter the OTP code.')
            return render(request, 'accounts/verify_password_reset_otp.html', {'email': reset_email})
        
        try:
            user = User.objects.get(email=reset_email)
            profile = user.profile
            
            if profile.is_otp_valid(otp):
                request.session['reset_user_id'] = user.id
                messages.success(request, '✅ OTP verified! Please set your new password.')
                logger.info(f"Password reset OTP verified for: {reset_email}")
                return redirect('set_new_password')
            else:
                if profile.otp_created_at:
                    time_diff = (timezone.now() - profile.otp_created_at).total_seconds()
                    if time_diff > 300:
                        messages.error(request, '❌ OTP has expired. Please request a new password reset.')
                        return redirect('forgot_password')
                
                messages.error(request, '❌ Invalid OTP code. Please try again.')
                logger.warning(f"Invalid password reset OTP attempt for: {reset_email}")
                
        except User.DoesNotExist:
            messages.error(request, '❌ User not found. Please start password reset again.')
            return redirect('forgot_password')
        except Exception as e:
            logger.error(f"Password reset OTP verification error: {e}")
            messages.error(request, '❌ An error occurred. Please try again.')
    
    return render(request, 'accounts/verify_password_reset_otp.html', {'email': reset_email})


def set_new_password(request):
    reset_user_id = request.session.get('reset_user_id')
    
    if not reset_user_id:
        messages.error(request, '❌ Invalid password reset session. Please start again.')
        return redirect('forgot_password')
    
    if request.method == 'POST':
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        if not password1 or not password2:
            messages.error(request, '❌ Please fill in both password fields.')
            return render(request, 'accounts/set_new_password.html')
        
        if password1 != password2:
            messages.error(request, '❌ Passwords do not match.')
            return render(request, 'accounts/set_new_password.html')
        
        if len(password1) < 8:
            messages.error(request, '❌ Password must be at least 8 characters long.')
            return render(request, 'accounts/set_new_password.html')
        
        try:
            user = User.objects.get(id=reset_user_id)
            user.set_password(password1)
            user.save()
            
            if 'reset_email' in request.session:
                del request.session['reset_email']
            if 'reset_user_id' in request.session:
                del request.session['reset_user_id']
            
            try:
                AuthEmailService.send_password_changed_email(user)
            except Exception as e:
                logger.error(f"Failed to send password changed email: {e}")
            
            messages.success(request, 
                '🔒 Password reset successfully! You can now log in with your new password.')
            logger.info(f"Password reset completed for user: {user.email}")
            return redirect('login')
            
        except User.DoesNotExist:
            messages.error(request, '❌ User not found. Please start password reset again.')
            return redirect('forgot_password')
        except Exception as e:
            logger.error(f"Password reset error: {e}")
            messages.error(request, '❌ Failed to reset password. Please try again.')
    
    return render(request, 'accounts/set_new_password.html')

from accounts.decorators import email_verified_required

@email_verified_required
def profile(request):
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user, is_email_verified=True)
    
    context = {
        'user': request.user,
        'profile': profile,
    }
    return render(request, 'accounts/profile.html', context)

@email_verified_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Password changed successfully!')
            return redirect('profile')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})
