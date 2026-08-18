from django.urls import path
from . import views

urlpatterns = [
    path('terms-and-conditions/', views.terms_and_conditions, name='terms_and_conditions'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('<slug:slug>/', views.page_detail, name='page_detail'),
]
