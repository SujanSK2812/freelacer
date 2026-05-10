
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from .models import Message
from django.contrib.auth.decorators import login_required

User = get_user_model()


@login_required
def chat_home(request):

    users = User.objects.exclude(id=request.user.id)

    return render(request, 'messages/chat_home.html', {
        'users': users
    })


@login_required
def chat_detail(request, user_id):

    other_user = get_object_or_404(User, id=user_id)

    messages = Message.objects.filter(
        sender__in=[request.user, other_user],
        receiver__in=[request.user, other_user]
    ).order_by('timestamp')

    if request.method == 'POST':
        text = request.POST.get('message')

        if text:
            Message.objects.create(
                sender=request.user,
                receiver=other_user,
                message=text
            )

        return redirect('chat_detail', user_id=other_user.id)

    return render(request, 'messages/chat_detail.html', {
        'other_user': other_user,
        'messages': messages
    })