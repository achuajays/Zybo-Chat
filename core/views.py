from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Max
from django.utils import timezone

from .models import User, Message
from .forms import CustomUserCreationForm, LoginForm


def register_view(request):
    """Handle user registration."""
    if request.user.is_authenticated:
        return redirect('user_list')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('user_list')
    else:
        form = CustomUserCreationForm()

    return render(request, 'core/register.html', {'form': form})


def login_view(request):
    """Handle user login."""
    if request.user.is_authenticated:
        return redirect('user_list')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user is not None:
                user.is_online = True
                user.save(update_fields=['is_online'])
                login(request, user)
                return redirect('user_list')
            else:
                messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()

    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    """Handle user logout."""
    if request.user.is_authenticated:
        request.user.is_online = False
        request.user.last_seen = timezone.now()
        request.user.save(update_fields=['is_online', 'last_seen'])
    logout(request)
    return redirect('login')


@login_required
def user_list_view(request):
    """Display all users except the current user, with unread counts."""
    from django.db.models import Count
    users_qs = User.objects.exclude(id=request.user.id)

    # Annotate each user with unread message count from them
    users_with_unread = []
    for user in users_qs:
        unread = Message.objects.filter(
            sender=user, receiver=request.user, is_read=False
        ).count()
        users_with_unread.append({'user': user, 'unread_count': unread})

    return render(request, 'core/user_list.html', {'users': users_with_unread})


@login_required
def chat_view(request, user_id):
    """Display chat interface for a specific user."""
    other_user = get_object_or_404(User, id=user_id)

    # Get message history between the two users
    chat_messages = Message.objects.filter(
        (Q(sender=request.user) & Q(receiver=other_user)) |
        (Q(sender=other_user) & Q(receiver=request.user))
    ).order_by('timestamp')

    # Mark unread messages as read
    Message.objects.filter(
        sender=other_user,
        receiver=request.user,
        is_read=False
    ).update(is_read=True)

    # Get recent chats for sidebar
    recent_chat_users = _get_recent_chats(request.user)

    return render(request, 'core/chat.html', {
        'other_user': other_user,
        'messages': chat_messages,
        'recent_chats': recent_chat_users,
    })


def _get_recent_chats(user):
    """Get list of users the current user has chatted with, most recent first."""
    # Get users who have exchanged messages with the current user
    sent_to = Message.objects.filter(sender=user).values_list('receiver', flat=True).distinct()
    received_from = Message.objects.filter(receiver=user).values_list('sender', flat=True).distinct()
    chat_user_ids = set(sent_to) | set(received_from)

    if not chat_user_ids:
        return []

    chat_users = User.objects.filter(id__in=chat_user_ids)

    # Annotate with last message time for ordering
    users_with_last_msg = []
    for chat_user in chat_users:
        last_msg = Message.objects.filter(
            (Q(sender=user) & Q(receiver=chat_user)) |
            (Q(sender=chat_user) & Q(receiver=user))
        ).order_by('-timestamp').first()

        unread_count = Message.objects.filter(
            sender=chat_user, receiver=user, is_read=False
        ).count()

        if last_msg:
            users_with_last_msg.append({
                'user': chat_user,
                'last_message': last_msg,
                'unread_count': unread_count,
            })

    users_with_last_msg.sort(key=lambda x: x['last_message'].timestamp, reverse=True)
    return users_with_last_msg
