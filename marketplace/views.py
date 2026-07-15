from django.shortcuts import render
from django.http import HttpResponse
from products.models import Product,Category

def home(request):
    product = Product.objects.all()
    return render(request, 'home/home.html',{'product':product})