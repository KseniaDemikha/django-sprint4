from .forms import PostForm, CommentForm
from .models import Post, Category, Comment
from .constants import NUMBER_OF_POSTS
from django.utils import timezone
from django.urls import reverse, reverse_lazy
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import HttpResponseNotFound
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import (
    CreateView, DetailView, ListView, UpdateView, DeleteView
)


class OnlyAuthorMixin(LoginRequiredMixin):
    """
    Проверяет, что авторизованный пользователь является автором редактируемого/
    удаляемого поста или комментария. Если нет, то перенаправляет на просмотр
    страницы этого поста.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user != self.get_object().author:
            return redirect('blog:post_detail',
                            self.kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)


class PostListView(ListView):
    """Отображает главную страницу блога."""

    model = Post
    paginate_by = NUMBER_OF_POSTS
    template_name = 'blog/index.html'

    def get_queryset(self):
        return Post.objects.filter(
            pub_date__lte=timezone.now(),
            is_published=True,
            category__is_published=True,
        ).annotate(comment_count=Count('comment')).order_by('-pub_date')


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'
    queryset = Post.objects.prefetch_related(
        'category',
        'location',
        'author'
    )

    def dispatch(self, request, *args, **kwargs):
        if (
            request.user != self.get_object().author
            and (self.get_object().is_published is False
                 or self.get_object().category.is_published is False
                 or self.get_object().pub_date > timezone.now())
        ):
            return HttpResponseNotFound('<h1>Страница не найдена</h1>')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        context['form'] = CommentForm(initial={'post': post})
        context['comments'] = Comment.objects.filter(post=post)
        return context


def category_posts(request, category_slug):
    """Отображает категории постов"""
    template = 'blog/category.html'
    category = get_object_or_404(
        Category, slug=category_slug, is_published=True)
    post_list = category.posts.filter(
        is_published=True,
        pub_date__lte=timezone.now()
    )
    paginator = Paginator(post_list, NUMBER_OF_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj, 'category': category}
    return render(request, template, context)


class ProfileListView(ListView):
    model = Post
    paginate_by = NUMBER_OF_POSTS
    template_name = 'blog/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = get_object_or_404(
            User,
            username=self.kwargs['username']
        )
        return context

    def get_queryset(self):
        return Post.objects.filter(
            author__username=self.kwargs['username']
        ).annotate(comment_count=Count('comment')).order_by('-pub_date')


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = 'blog/user.html'
    fields = ['first_name', 'last_name', 'username', 'email']

    def get_success_url(self):
        return reverse(
            'blog:profile',
            args=[self.request.user.username])

    def get_object(self, queryset=None):
        return self.request.user


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def get_success_url(self):
        return reverse(
            'blog:profile',
            kwargs={'username': self.request.user.username}
        )

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.pub_date = form.cleaned_data['pub_date']
        return super().form_valid(form)


class PostUpdateView(OnlyAuthorMixin, UpdateView):
    model = Post
    fields = ('title', 'text', 'location', 'category', 'image', 'pub_date')
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.id})


class PostDeleteView(OnlyAuthorMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    success_url = reverse_lazy('blog:index')
    pk_url_kwarg = 'post_id'


@login_required
def add_comment(request, post_id):
    """Добавление комментария."""
    post = get_object_or_404(Post, id=post_id)

    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
    return redirect('blog:post_detail', post_id=post.id)


class CommentUpdateView(OnlyAuthorMixin, UpdateView):
    model = Comment
    fields = ('text',)
    template_name = 'blog/comment.html'

    def get_success_url(self):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.object.post.id}
        )

    def get_object(self, queryset=None):
        return get_object_or_404(
            Comment,
            id=self.kwargs['comment_id'],
            post__id=self.kwargs['post_id']
        )


class CommentDeleteView(OnlyAuthorMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'

    def get_success_url(self):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.object.post.id}
        )

    def get_object(self, queryset=None):
        return get_object_or_404(
            Comment,
            id=self.kwargs['comment_id'],
            post__id=self.kwargs['post_id']
        )
