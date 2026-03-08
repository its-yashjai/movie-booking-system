from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.views import View
from django.http import FileResponse
import os

class MediaServeView(View):
    def get(self, request, path):
        file_path = os.path.join(settings.MEDIA_ROOT, path)
        if os.path.isfile(file_path):
            return FileResponse(open(file_path, 'rb'), content_type='application/octet-stream')
        from django.http import Http404
        raise Http404(f"Media file not found: {path}")

def home_redirect(request):

    return redirect('login')

urlpatterns = [
    path('custom-admin/', include('custom_admin.urls')),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('bookings/', include('bookings.urls')),
    path('', include('movies.urls')),  # Include movies app URLs (handles home page)
]

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        path('media/<path:path>', serve, {
            'document_root': settings.MEDIA_ROOT,
            'show_indexes': False
        }),
    ]