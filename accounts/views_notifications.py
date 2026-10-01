from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Notification

@login_required
def mark_notifications_read(request):
    if request.method == "POST":
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)

@login_required
def delete_notification(request, notification_id):
    if request.method == "POST":
        notif = Notification.objects.filter(id=notification_id, user=request.user).first()
        if notif:
            notif.delete()
            unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
            total_count = Notification.objects.filter(user=request.user).count()
            return JsonResponse({
                "status": "success",
                "unread_count": unread_count,
                "total_count": total_count
            })
        return JsonResponse({"status": "error", "message": "Notification not found"}, status=404)
    return JsonResponse({"status": "error"}, status=400)

@login_required
def clear_all_notifications(request):
    if request.method == "POST":
        Notification.objects.filter(user=request.user).delete()
        return JsonResponse({"status": "success", "unread_count": 0, "total_count": 0})
    return JsonResponse({"status": "error"}, status=400)
