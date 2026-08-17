from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Category, Post

def blog(request):
    blogs = Post.objects.select_related('category', 'author').filter(status=True)
    author_q = request.GET.get('author')
    if author_q:
        blogs = blogs.filter(author__username=author_q)
    return render(request, 'blog/blog.html', {'blogs': blogs, 'categories': Category.objects.all(), 'author_q': author_q})

def blog_detail(request, id):
    p = get_object_or_404(Post.objects.select_related('category', 'author'), pk=id)
    return render(request, 'blog/blog_detail.html', {'blog': p, 'recent_blogs': Post.objects.exclude(pk=id)[:4]})

@login_required
def blog_create(request):
    if request.method == 'POST':
        Post.objects.create(
            author=request.user,
            title=request.POST['title'],
            category_id=request.POST.get('category') or Category.objects.first().id,
            content=request.POST['content'],
            post_image=request.FILES.get('post_image')
        )
        return redirect('blog')
    return render(request, 'blog/blog_create.html', {'categories': Category.objects.all()})

def user_blogs(request, username):
    author = get_object_or_404(User, username=username)
    return render(request, 'blog/blog.html', {'blogs': Post.objects.filter(author=author, status=True), 'categories': Category.objects.all(), 'author_q': username})