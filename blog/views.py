from django.shortcuts import render, get_object_or_404
from .models import Category, Post

def blog(request):
    blogs = Post.objects.select_related('category').filter(status=True).order_by('-created_at')
    if not blogs.exists():
        blogs = Post.objects.select_related('category').all().order_by('-created_at')
    categories = Category.objects.all()
    return render(request, 'blog/blog.html', {
        'blogs': blogs,
        'categories': categories,
    })

def blog_detail(request, id):
    blog = get_object_or_404(Post, pk=id)
    recent_blogs = Post.objects.exclude(pk=id)[:4]
    return render(request, 'blog/blog_detail.html', {
        'blog': blog,
        'recent_blogs': recent_blogs,
    })