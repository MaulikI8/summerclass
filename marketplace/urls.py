from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views
from sitesetting import views as site_views
from pages.views import page_detail

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('login/', views.student_login, name='student_login'),
    path('register/', views.student_register, name='student_register'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('logout/', views.student_logout, name='student_logout'),
    path('profile/', views.user_profile, name='user_profile'),
    path('api/notifications/', site_views.api_notifications, name='api_notifications'),
    path('api/notifications/read/', site_views.api_notification_read, name='api_notification_read'),
    path('api/notifications/read-all/', site_views.api_notification_read_all, name='api_notification_read_all'),
    path('404/', views.custom_404, name='preview_404'),
    path('blogs/', include('blog.urls')),
    path('products/', include('products.urls')),
    path('<slug:slug>/', page_detail, name='page_detail'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'marketplace.views.custom_404'
