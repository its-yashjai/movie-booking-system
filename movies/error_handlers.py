import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError

logger = logging.getLogger(__name__)

def handler400(request, exception):

    logger.warning(f'400 Error: {exception}')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'error': 'Bad Request',
            'message': 'The request could not be understood.'
        }, status=400)
    
    return render(request, 'errors/400.html', status=400)

def handler403(request, exception):

    logger.warning(f'403 Error: {exception}')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'error': 'Forbidden',
            'message': 'You do not have permission to access this resource.'
        }, status=403)
    
    return render(request, 'errors/403.html', status=403)

def handler404(request, exception):

    logger.warning(f'404 Error: {exception}')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'error': 'Not Found',
            'message': 'The requested resource was not found.'
        }, status=404)
    
    return render(request, 'errors/404.html', status=404)

def handler500(request):

    logger.error('500 Internal Server Error')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred.'
        }, status=500)
    
    return render(request, 'errors/500.html', status=500)

def handler503(request, exception=None):

    logger.error('503 Service Unavailable')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'error': 'Service Unavailable',
            'message': 'The service is temporarily unavailable.'
        }, status=503)
    
    return render(request, 'errors/503.html', status=503)

class GlobalExceptionMiddleware:

    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_exception(self, request, exception):

        logger.error(f'Unhandled exception: {exception}', exc_info=True)
        
        if isinstance(exception, DatabaseError):
            return handler503(request, exception)
        elif isinstance(exception, PermissionDenied):
            return handler403(request, exception)
        
        return None