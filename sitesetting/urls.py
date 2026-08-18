from django.urls import path
from . import views

urlpatterns = [
    path('notifications/', views.api_notifications, name='api_notifications'),
    path('notifications/read/', views.api_notification_read, name='api_notification_read'),
    path('notifications/read-all/', views.api_notification_read_all, name='api_notification_read_all'),
]
