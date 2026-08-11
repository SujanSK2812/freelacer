from django.db import models
from django.conf import settings
from projects.models import Job


class Proposal(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    ]

    freelancer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="proposals"
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="job_proposals"
    )

    proposal_text = models.TextField()

    bid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    delivery_days = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        unique_together = ("freelancer", "job")

    def __str__(self):
        return f"{self.freelancer} -> {self.job.title}"