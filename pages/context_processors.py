from .models import Page

def page_links(request):
    try:
        return {'pages': list(Page.objects.all())}
    except Exception:
        return {'pages': []}