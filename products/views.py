from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from . models import Category, Product

# Create your views here.

def products(request):
    product = Product.objects.all()
    return render(request, 'products/products.html', {'product': product})

def product_detail(request,id):
    product = get_object_or_404(Product,pk=id)
    return render(request, 'products/product_detail.html', {'product':product})