from django.contrib import admin
from django.urls import path, include, re_path
from django.shortcuts import redirect
from django.conf import settings
from django.views.static import serve
from . import views
from account import views as account_views
from pages import views as page_views

urlpatterns = [
    path('admin', lambda req: redirect('/admin/', permanent=False)),
    path('admin/', admin.site.urls),
    path('seed-store-now/', views.seed_store_view, name='seed_store_now'),
    path('', views.home, name='home'),
    path('account/', include('account.urls')),
    path('login/', account_views.student_login, name='student_login'),
    path('register/', account_views.student_register, name='student_register'),
    path('activate/<str:uidb64>/<str:token>/', account_views.activate_account, name='activate_account'),
    path('verify-otp/', account_views.verify_otp, name='verify_otp'),
    path('resend-otp/', account_views.resend_otp, name='resend_otp'),
    path('verify-email/<str:token>/', account_views.verify_email, name='verify_email'),
    path('logout/', account_views.student_logout, name='student_logout'),
    path('profile/', account_views.user_profile, name='user_profile'),
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/khalti/<int:order_id>/', views.khalti_pay, name='khalti_pay'),
    path('checkout/khalti/complete/', views.khalti_complete, name='khalti_complete'),
    path('cart/', include('cart.urls')),
    path('checkout/success/<int:order_id>/', views.order_success, name='order_success'),
    path('place-bid/<int:auction_id>/', views.place_bid, name='place_bid'),
    path('start-auction/<int:product_id>/', views.start_auction, name='start_auction'),
    path('accept-auction/<int:auction_id>/', views.accept_auction_bid, name='accept_auction_bid'),
    path('api/', include('sitesetting.urls')),
    path('api/chatbot/', views.api_chatbot, name='api_chatbot'),
    path('pages/', include('pages.urls')),
    path('terms-and-conditions/', page_views.terms_and_conditions, name='terms_and_conditions'),
    path('terms/', page_views.terms_and_conditions),
    path('trading-guidelines/', page_views.terms_and_conditions),
    path('privacy-policy/', page_views.privacy_policy, name='privacy_policy'),
    path('privacy/', page_views.privacy_policy),
    path('404/', views.custom_404, name='preview_404'),
    path('blogs/', include('blog.urls')),
    path('blog/', include('blog.urls')),
    path('products/', include('products.urls')),
    path('page/<slug:slug>/', page_views.page_detail, name='page_detail'),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]

handler404 = 'marketplace.views.custom_404'
