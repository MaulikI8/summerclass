from django.shortcuts import render, get_object_or_404
from .models import Category, Post

def blog(request):
    blogs = Post.objects.select_related('category').filter(status=True).order_by('-created_at') or Post.objects.select_related('category').all().order_by('-created_at')
    return render(request, 'blog/blog.html', {'blogs': blogs, 'categories': Category.objects.all()})

def blog_detail(request, id):
    p = get_object_or_404(Post, pk=id)
    return render(request, 'blog/blog_detail.html', {'blog': p, 'recent_blogs': Post.objects.exclude(pk=id)[:4]})