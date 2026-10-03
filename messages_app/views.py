
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages as django_messages
from django.contrib.auth import get_user_model
from .models import Message
from django.db.models import Q
from django.contrib.auth.decorators import login_required

from accounts.models import Connection, ConnectionRequest
from proposals.models import Proposal

User = get_user_model()


def get_chat_partners_list(current_user, active_partner=None):
    from django.utils import timezone

    # 1. Partner IDs from exchanged messages
    partner_ids = Message.objects.filter(
        Q(sender=current_user) | Q(receiver=current_user)
    ).values_list('sender_id', 'receiver_id')
    
    chat_partner_ids = set()
    for s_id, r_id in partner_ids:
        if s_id != current_user.id:
            chat_partner_ids.add(s_id)
        if r_id != current_user.id:
            chat_partner_ids.add(r_id)

    # 2. Add all Connection partners (connections where current_user is sender or receiver)
    conn_pairs = Connection.objects.filter(
        Q(sender=current_user) | Q(receiver=current_user)
    ).values_list('sender_id', 'receiver_id')
    for s_id, r_id in conn_pairs:
        if s_id != current_user.id:
            chat_partner_ids.add(s_id)
        if r_id != current_user.id:
            chat_partner_ids.add(r_id)

    # 3. Add all accepted ConnectionRequests
    cr_pairs = ConnectionRequest.objects.filter(
        (Q(sender=current_user) | Q(receiver=current_user)),
        status='accepted'
    ).values_list('sender_id', 'receiver_id')
    for s_id, r_id in cr_pairs:
        if s_id != current_user.id:
            chat_partner_ids.add(s_id)
        if r_id != current_user.id:
            chat_partner_ids.add(r_id)

    # 4. Include active partner if provided
    if active_partner and active_partner.id != current_user.id:
        chat_partner_ids.add(active_partner.id)

    if not chat_partner_ids:
        return []

    users_qs = User.objects.filter(id__in=chat_partner_ids)
    user_list = list(users_qs)

    for u in user_list:
        last_msg = Message.objects.filter(
            Q(sender=current_user, receiver=u, deleted_by_sender=False) |
            Q(sender=u, receiver=current_user, deleted_by_receiver=False)
        ).order_by('-timestamp').first()
        u.last_message = last_msg

        # Filter metrics
        u.unread_count = Message.objects.filter(
            sender=u, receiver=current_user, is_read=False, deleted_by_receiver=False
        ).count()

        u.is_connection = Connection.objects.filter(
            (Q(sender=current_user, receiver=u) | Q(sender=u, receiver=current_user))
        ).exists() or ConnectionRequest.objects.filter(
            (Q(sender=current_user, receiver=u) | Q(sender=u, receiver=current_user)),
            status='accepted'
        ).exists()

        has_proposal = Proposal.objects.filter(
            (Q(job__client=current_user, freelancer=u) | Q(job__client=u, freelancer=current_user))
        ).exists()
        has_msg_job = Message.objects.filter(
            (Q(sender=u, receiver=current_user) | Q(sender=current_user, receiver=u)),
            proposal__isnull=False
        ).exists()
        u.has_jobs = has_proposal or has_msg_job

        u.is_inmail = not u.is_connection

        u.is_focused = u.is_connection or u.has_jobs or (u.last_message is not None)

    # Sort users:
    # 1. Users with messages sorted by most recent timestamp
    # 2. Connections without messages sorted by date_joined
    epoch = timezone.now().replace(year=2000)
    user_list.sort(
        key=lambda u: (
            1 if (getattr(u, 'last_message', None) and u.last_message) else 0,
            u.last_message.timestamp if (getattr(u, 'last_message', None) and u.last_message) else (getattr(u, 'date_joined', None) or epoch),
        ),
        reverse=True
    )
    return user_list


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

    user_list = get_chat_partners_list(request.user)

    # If messages exist, open the most recent chat partner
    latest_msg = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).order_by('-timestamp').first()
    
    if latest_msg:
        first_user_id = latest_msg.receiver_id if latest_msg.sender_id == request.user.id else latest_msg.sender_id
        return redirect('chat_detail', user_id=first_user_id)

    following_count = Connection.objects.filter(sender=request.user).count()
    followers_count = Connection.objects.filter(receiver=request.user).count()

    return render(request, 'messages/chat_home.html', {
        'other_user': None,
        'messages': [],
        'users': user_list,
        'following_count': following_count,
        'followers_count': followers_count,
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

    # Mark incoming messages as read
    Message.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)

    if request.method == "POST":
        text = request.POST.get("message", "").strip()
        image = request.FILES.get("image")
        attachment = request.FILES.get("attachment")
        gif_url = request.POST.get("gif_url", "").strip()

        if text or image or attachment or gif_url:
            file_name = None
            file_size = None
            if attachment:
                file_name = attachment.name
                size_bytes = attachment.size
                if size_bytes < 1024:
                    file_size = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    file_size = f"{size_bytes / 1024:.1f} KB"
                else:
                    file_size = f"{size_bytes / (1024 * 1024):.1f} MB"

            Message.objects.create(
                sender=request.user,
                receiver=other_user,
                message=text,
                image=image,
                file_attachment=attachment,
                file_name=file_name,
                file_size=file_size,
                gif_url=gif_url or None
            )

        return redirect('chat_detail', user_id=other_user.id)

    user_list = get_chat_partners_list(request.user, active_partner=other_user)

    following_count = Connection.objects.filter(sender=request.user).count()
    followers_count = Connection.objects.filter(receiver=request.user).count()

    return render(request, 'messages/chat_home.html', {
        'other_user': other_user,
        'messages': messages,
        'users': user_list,
        'following_count': following_count,
        'followers_count': followers_count,
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
        
    return redirect(f"{reverse('chat_detail', kwargs={'user_id': other_user.id})}?cleared=1")


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