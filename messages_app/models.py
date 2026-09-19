
from django.db import models
from django.conf import settings

class Message(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )

    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages'
    )

    message = models.TextField()

    timestamp = models.DateTimeField(auto_now_add=True)

    is_read = models.BooleanField(default=False)
    
    deleted_by_sender = models.BooleanField(default=False)
    
    deleted_by_receiver = models.BooleanField(default=False)

    proposal = models.ForeignKey(
        'proposals.Proposal', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='messages'
    )

    def __str__(self):
        return f"{self.sender} -> {self.receiver}"