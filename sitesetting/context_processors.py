from .models import SiteSetting

def site_settings(request):
    try:
        setting = SiteSetting.objects.first()
        return {'site_setting': setting}
    except Exception:
        return {'site_setting': None}
