from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.utils.timesince import timesince
from .models import Notification

@require_GET
def api_notifications(request):
    if not request.user.is_authenticated: return JsonResponse({'unread_count': 0, 'notifications': []})
    qs = Notification.objects.filter(recipient=request.user)
    notifs = [{'id': n.id, 'type': n.notif_type, 'title': n.title, 'message': n.message, 'icon': n.icon, 'link': n.link, 'is_read': n.is_read, 'time_ago': f"{timesince(n.created_at)} ago"} for n in qs.order_by('-created_at')[:20]]
    return JsonResponse({'unread_count': qs.filter(is_read=False).count(), 'notifications': notifs})

@require_POST
def api_notification_read(request):
    if request.user.is_authenticated: Notification.objects.filter(id=request.POST.get('id'), recipient=request.user).update(is_read=True)
    return JsonResponse({'status': 'ok'})

@require_POST
def api_notification_read_all(request):
    if request.user.is_authenticated: Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'ok'})
