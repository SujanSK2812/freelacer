from datetime import timedelta
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

    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the bid was accepted by the client."
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        unique_together = ("freelancer", "job")

    @property
    def expected_completion_date(self):
        if self.accepted_at and self.delivery_days:
            return self.accepted_at + timedelta(days=self.delivery_days)
        return None

    @property
    def job_has_accepted_proposal(self):
        return Proposal.objects.filter(job=self.job, status="accepted").exists()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # If accepted bid's estimated days or acceptance time changes, update project completion date
        if self.status == "accepted" and self.accepted_at and self.job_id:
            target_date = self.accepted_at + timedelta(days=self.delivery_days)
            job = self.job
            if job.expected_completion_date != target_date or job.accepted_at != self.accepted_at:
                job.accepted_at = self.accepted_at
                job.expected_completion_date = target_date
                job.save(update_fields=["accepted_at", "expected_completion_date"])

    def __str__(self):
        return f"{self.freelancer} -> {self.job.title}"