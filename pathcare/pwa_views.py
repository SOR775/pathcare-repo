from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.http import HttpResponse

def offline_view(request):
    """Serve the offline page for PWA"""
    return render(request, 'offline.html', status=503)

@cache_page(60 * 60 * 24)  # Cache for 24 hours
def manifest_view(request):
    """Serve the manifest.json for PWA with correct content type"""
    manifest_path = 'manifest.json'
    with open(f'tracking/static/{manifest_path}', 'r') as f:
        content = f.read()
    return HttpResponse(content, content_type='application/manifest+json')
