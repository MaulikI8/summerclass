from django.shortcuts import render
from . models import Category, Post
# Create your views here.

def blog(request):
    post = Post.objects.all()
    return render(request, 'blog/blog.html', {'post': post})

def blog_detail(request,id):
    post = Post.objects.get(id=id)
    return render(request, 'blog/blog_detail.html', {'post': post})
