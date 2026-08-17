from django.urls import path
from . import views

urlpatterns = [
    path('', views.blog, name='blog'),
    path('create/', views.blog_create, name='blog_create'),
    path('<int:id>/', views.blog_detail, name='blog_detail'),
    path('user/<str:username>/', views.user_blogs, name='user_blogs'),
]
