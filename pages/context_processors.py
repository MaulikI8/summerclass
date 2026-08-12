from . models import Page

def page_links(request):
    return {'pages' : Page.objects.all()}