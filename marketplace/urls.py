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
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/success/<int:order_id>/', views.order_success, name='order_success'),
    path('place-bid/<int:auction_id>/', views.place_bid, name='place_bid'),
    path('start-auction/<int:product_id>/', views.start_auction, name='start_auction'),
    path('accept-auction/<int:auction_id>/', views.accept_auction_bid, name='accept_auction_bid'),
    path('logout/', views.student_logout, name='student_logout'),
    path('profile/', views.user_profile, name='user_profile'),
    path('api/notifications/', site_views.api_notifications, name='api_notifications'),
    path('api/notifications/read/', site_views.api_notification_read, name='api_notification_read'),
    path('api/notifications/read-all/', site_views.api_notification_read_all, name='api_notification_read_all'),
    path('404/', views.custom_404, name='preview_404'),
    path('blogs/', include('blog.urls')),
    path('products/', include('products.urls')),
    path('<slug:slug>/', page_detail, name='page_detail'),
]

from django.views.static import serve
from django.urls import re_path

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]

handler404 = 'marketplace.views.custom_404'
