import logging
from django.utils import timezone
from django.db import transaction
from django.urls import reverse
from projects.models import Job

logger = logging.getLogger(__name__)


def auto_complete_expired_projects():
    """
    Checks all in-progress jobs whose accepted proposal's expected completion date
    has passed (now >= expected_completion_date).
    Marks the job as completed, deactivates it (is_active=False) so it cannot receive new bids,
    and removes it from active project searches/listings.
    
    IMPORTANT:
    - Does NOT alter payment records or automatically mark projects as paid.
    - Prevents duplicate processing via atomic transactions and row-level locking.
    - Preserves all bids, messages, and project history intact.
    
    Returns:
        int: Number of projects transitioned to completed/deactivated.
    """
    now = timezone.now()
    
    # Identify in-progress projects that have passed their expected completion date
    expired_job_ids = list(
        Job.objects.filter(
            status='in_progress',
            expected_completion_date__isnull=False,
            expected_completion_date__lte=now
        ).values_list('id', flat=True)
    )

    if not expired_job_ids:
        return 0

    completed_count = 0
    from accounts.models import Notification

    for job_id in expired_job_ids:
        try:
            with transaction.atomic():
                # Lock row to prevent duplicate/concurrent processing
                job = Job.objects.select_for_update().filter(id=job_id, status='in_progress').first()
                if not job or not job.expected_completion_date or job.expected_completion_date > now:
                    continue

                job.status = 'completed'
                job.is_active = False
                job.save(update_fields=['status', 'is_active'])
                completed_count += 1

                # Send non-disruptive notifications
                try:
                    Notification.objects.create(
                        user=job.client,
                        notification_type='general',
                        message=f"The project <strong>{job.title}</strong> has reached its estimated delivery deadline and is now marked as <strong>Completed</strong>.",
                        link=reverse('client:client_dashboard')
                    )

                    accepted_proposal = job.accepted_proposal
                    if accepted_proposal and accepted_proposal.freelancer:
                        Notification.objects.create(
                            user=accepted_proposal.freelancer,
                            notification_type='general',
                            message=f"Contract for <strong>{job.title}</strong> has reached its estimated completion period and is now marked as <strong>Completed</strong>.",
                            link=reverse('freelancer:active_contracts')
                        )
                except Exception as notif_err:
                    logger.warning(f"Could not dispatch completion notification for Job #{job.id}: {notif_err}")

        except Exception as e:
            logger.error(f"Error auto-completing expired Job #{job_id}: {e}")

    return completed_count
