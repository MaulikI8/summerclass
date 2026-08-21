from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db.models import Count
from .models import Category, Post, Comment
from sitesetting.models import Notification

def blog(request):
    cat, tag, author, sort = request.GET.get('category'), request.GET.get('tag'), request.GET.get('author'), request.GET.get('sort')
    posts = Post.objects.select_related('category', 'author').prefetch_related('comments', 'upvotes').filter(status=True)
    if cat: posts = posts.filter(category__name__iexact=cat)
    if tag: posts = posts.filter(tag__iexact=tag)
    if author: posts = posts.filter(author__username=author)
    posts = posts.annotate(upvote_cnt=Count('upvotes')).order_by('-upvote_cnt' if sort == 'top' else '-created_at')
    
    return render(request, 'blog/blog.html', {
        'blogs': posts, 'categories': Category.objects.all(),
        'selected_cat': cat, 'selected_tag': tag, 'selected_author': author, 'sort': sort
    })

def blog_detail(request, id):
    p = get_object_or_404(Post.objects.select_related('category', 'author').prefetch_related('comments__author', 'upvotes'), pk=id)
    has_upvoted = request.user.is_authenticated and p.upvotes.filter(id=request.user.id).exists()
    return render(request, 'blog/blog_detail.html', {'blog': p, 'comments': p.comments.all(), 'has_upvoted': has_upvoted})

@login_required
def blog_create(request):
    if request.method == 'POST':
        c, _ = Category.objects.get_or_create(name=request.POST.get('category') or 'General') if not request.POST.get('category_id') else (Category.objects.get(id=request.POST['category_id']), False)
        p = Post.objects.create(
            author=request.user, title=request.POST['title'].strip(),
            category=c, tag=request.POST.get('tag', 'Discussion'),
            content=request.POST['content'].strip(), post_image=request.FILES.get('post_image')
        )
        return redirect('blog_detail', id=p.id)
    return render(request, 'blog/blog_create.html', {'categories': Category.objects.all()})

@login_required
def add_comment(request, id):
    if request.method == 'POST' and request.POST.get('content'):
        p = get_object_or_404(Post, pk=id)
        c = Comment.objects.create(post=p, author=request.user, content=request.POST['content'].strip())
        if p.author and p.author != request.user:
            Notification.notify(p.author, f"New reply on '{p.title[:30]}'", f"{request.user.username}: {c.content[:50]}", 'comment', 'fa-comment', f'/blogs/{p.id}/')
    return redirect('blog_detail', id=id)

@login_required
def toggle_upvote(request, id):
    p = get_object_or_404(Post, pk=id)
    if p.upvotes.filter(id=request.user.id).exists(): p.upvotes.remove(request.user); voted = False
    else: p.upvotes.add(request.user); voted = True
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'upvotes': p.upvotes.count(), 'voted': voted})
    return redirect(request.META.get('HTTP_REFERER', 'blog'))

def user_blogs(request, username):
    return redirect(f'/blogs/?author={username}')

@login_required
def blog_delete(request, id):
    p = get_object_or_404(Post, pk=id)
    if p.author == request.user or request.user.is_staff or request.user.is_superuser:
        title = p.title
        p.delete()
        messages.success(request, f'Blog post "{title[:30]}" deleted successfully.')
        return redirect('blog')
    messages.error(request, "You do not have permission to delete this post.")
    return redirect('blog_detail', id=id)