from django.urls import path
from . import views

urlpatterns = [
    path('', views.blog, name='blog'),
    path('create/', views.blog_create, name='blog_create'),
    path('<int:id>/', views.blog_detail, name='blog_detail'),
    path('<int:id>/delete/', views.blog_delete, name='blog_delete'),
    path('<int:id>/comment/', views.add_comment, name='add_comment'),
    path('<int:id>/upvote/', views.toggle_upvote, name='toggle_upvote'),
    path('user/<str:username>/', views.user_blogs, name='user_blogs'),
]
