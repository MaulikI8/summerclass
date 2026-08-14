from django.urls import path
from . import views

app_name = 'account'

urlpatterns = [
    path('login/', views.student_login, name='login'),
    path('register/', views.student_register, name='register'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('logout/', views.student_logout, name='logout'),
    path('profile/', views.user_profile, name='profile'),
]
