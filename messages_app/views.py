
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages as django_messages
from django.contrib.auth import get_user_model
from .models import Message
from django.db.models import Q
from django.contrib.auth.decorators import login_required

User = get_user_model()


@login_required
def chat_home(request):

    # If ?user=ID is passed (e.g. from "Message" button on proposals), go directly to that chat
    target_user_id = request.GET.get('user')
    if target_user_id:
        try:
            target_user = User.objects.get(id=target_user_id)
            return redirect('chat_detail', user_id=target_user.id)
        except User.DoesNotExist:
            pass

    # ADMIN
    if request.user.is_staff:
        users = User.objects.exclude(id=request.user.id)

    # CLIENT -> only freelancers
    elif request.user.role == "client":
        users = User.objects.filter(role="freelancer")

    # FREELANCER -> only clients
    elif request.user.role == "freelancer":
        users = User.objects.filter(role="client")

    else:
        users = User.objects.none()

    return render(request, 'messages/chat_home.html', {
        'users': users
    })


@login_required
def chat_detail(request, user_id):

    other_user = get_object_or_404(User, id=user_id)

    messages = Message.objects.filter(
        sender__in=[request.user, other_user],
        receiver__in=[request.user, other_user]
    ).exclude(
        Q(sender=request.user, deleted_by_sender=True) | 
        Q(receiver=request.user, deleted_by_receiver=True)
    ).order_by('timestamp')

    if request.method == "POST":

        text = request.POST.get("message")

        if text:
            Message.objects.create(
                sender=request.user,
                receiver=other_user,
                message=text
            )

        return redirect('chat_detail', user_id=other_user.id)

    if request.user.is_staff:
        users = User.objects.exclude(id=request.user.id)
    elif request.user.role == "client":
        users = User.objects.filter(role="freelancer")
    elif request.user.role == "freelancer":
        users = User.objects.filter(role="client")
    else:
        users = User.objects.none()

    return render(request, 'messages/chat_home.html', {
        'other_user': other_user,
        'messages': messages,
        'users': users,
    })


@login_required
def clear_chat(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    
    # Get all messages between these two users
    messages = Message.objects.filter(
        sender__in=[request.user, other_user],
        receiver__in=[request.user, other_user]
    )
    
    # Mark as deleted for current user
    for msg in messages:
        if msg.sender == request.user:
            msg.deleted_by_sender = True
        if msg.receiver == request.user:
            msg.deleted_by_receiver = True
        msg.save()
        
    django_messages.success(request, f"Chat with {other_user.username} has been cleared.")
    return redirect('chat_detail', user_id=other_user.id)


from accounts.models import ConnectionRequest, Connection
from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
def chat_user_list(request):

    # users who FOLLOWED current user (followers)
    followers_connections = Connection.objects.filter(
        receiver=request.user
    )

    followers = [conn.sender for conn in followers_connections]

    # users current user follows
    following_connections = Connection.objects.filter(
        sender=request.user
    )

    following = [conn.receiver for conn in following_connections]
    
    # Also include pending outgoing requests so client can message them immediately if desired
    pending_outgoing = ConnectionRequest.objects.filter(sender=request.user, status='pending')
    pending_following = [req.receiver for req in pending_outgoing]
    
    # users who sent pending requests to current user
    pending_incoming = ConnectionRequest.objects.filter(receiver=request.user, status='pending')
    pending_followers = [req.sender for req in pending_incoming]

    all_chat_users = list(set(followers + following + pending_following + pending_followers))

    # pending requests (incoming only for display in UI)
    received_requests = ConnectionRequest.objects.filter(
        receiver=request.user,
        status='pending'
    )

    context = {
        "users": all_chat_users,   # Include everyone connected or pending
        "followers": followers,
        "following": following,
        "received_requests": received_requests,
        "pending_requests_count": received_requests.count(),
    }

    return render(request, "messages/chat.html", context)