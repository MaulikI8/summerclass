from django.shortcuts import render
from .models import Page

def page_detail(request, slug):
    try:
        return render(request, 'pages/page_details.html', {'page': Page.objects.get(slug=slug)})
    except Page.DoesNotExist:
        return render(request, '404.html', status=404)

def terms_and_conditions(request):
    return render(request, 'pages/terms_and_conditions.html')

def privacy_policy(request):
    return render(request, 'pages/privacy_policy.html')
