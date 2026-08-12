from django.shortcuts import render
from .models import Page

def page_detail(request, slug):
    try:
        page = Page.objects.get(slug=slug)
        return render(request, 'pages/page_details.html', {'page': page})
    except Page.DoesNotExist:
        return render(request, '404.html', status=404)
