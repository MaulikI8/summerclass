from django.urls import path
from . import views

urlpatterns = [
    path('', views.products, name='products'),
    path('suggest/', views.search_suggest, name='search_suggest'),
    path('<int:id>/', views.product_detail, name='product_detail'),
    path('<int:id>/wishlist/', views.toggle_wishlist, name='toggle_wishlist'),
    path('<int:id>/offer/', views.send_offer, name='send_offer'),
    path('offer/<int:offer_id>/<str:action>/', views.respond_offer, name='respond_offer'),
    path('wanted/post/', views.post_item_request, name='post_item_request'),
    path('wanted/fulfill/<int:request_id>/', views.fulfill_item_request, name='fulfill_item_request'),
    path('wanted/delete/<int:request_id>/', views.delete_item_request, name='delete_item_request'),
]