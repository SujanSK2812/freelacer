from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from django.core.management import call_command
import io

from projects.models import Job
from proposals.models import Proposal
from payments.models import Payment
from projects.services import auto_complete_expired_projects

User = get_user_model()


class ProjectExpirationAndDeactivationTest(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            email="client_exp@example.com",
            username="client_exp",
            phone="1112223334",
            role="client",
            password="password123"
        )
        self.freelancer_user1 = User.objects.create_user(
            email="free1_exp@example.com",
            username="free1_exp",
            phone="2223334445",
            role="freelancer",
            password="password123"
        )
        self.freelancer_user2 = User.objects.create_user(
            email="free2_exp@example.com",
            username="free2_exp",
            phone="3334445556",
            role="freelancer",
            password="password123"
        )

        self.job = Job.objects.create(
            client=self.client_user,
            title="Full-Stack Web App Development",
            description="Build a high performance web application with Django and React.",
            budget="15000",
            skills="Django, React, Python",
            experience_level="Intermediate",
            status="open",
            is_active=True
        )

        self.client_http = Client()

    def test_calculate_project_completion_date_upon_acceptance(self):
        """Verify countdown only begins upon bid acceptance and correctly computes expected completion date."""
        # 1. Pending bid created
        proposal1 = Proposal.objects.create(
            freelancer=self.freelancer_user1,
            job=self.job,
            proposal_text="I can build this in 7 days.",
            bid_amount=14000.00,
            delivery_days=7,
            status="pending"
        )
        proposal2 = Proposal.objects.create(
            freelancer=self.freelancer_user2,
            job=self.job,
            proposal_text="I can build this in 10 days.",
            bid_amount=15000.00,
            delivery_days=10,
            status="pending"
        )

        # Before acceptance, job is open, countdown has not started
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "open")
        self.assertIsNone(self.job.accepted_at)
        self.assertIsNone(self.job.expected_completion_date)

        # Client logs in and accepts proposal 1
        self.client_http.login(email="client_exp@example.com", password="password123")
        accept_url = reverse("client:accept_proposal", args=[proposal1.id])
        response = self.client_http.post(accept_url)
        self.assertEqual(response.status_code, 302)

        # Refresh objects
        proposal1.refresh_from_db()
        proposal2.refresh_from_db()
        self.job.refresh_from_db()

        # Proposal 1 is accepted, proposal 2 is rejected
        self.assertEqual(proposal1.status, "accepted")
        self.assertIsNotNone(proposal1.accepted_at)
        self.assertEqual(proposal2.status, "rejected")
        self.assertIsNone(proposal2.accepted_at)

        # Job is now in_progress with completion date = accepted_at + 7 days
        self.assertEqual(self.job.status, "in_progress")
        self.assertTrue(self.job.is_active)
        self.assertIsNotNone(self.job.accepted_at)
        expected_date = self.job.accepted_at + timedelta(days=7)
        self.assertEqual(self.job.expected_completion_date, expected_date)
        self.assertEqual(self.job.estimated_days, 7)

    def test_update_completion_date_when_estimated_days_change(self):
        """If an accepted bid's estimated days change through an authorized process, update completion date."""
        now = timezone.now()
        proposal = Proposal.objects.create(
            freelancer=self.freelancer_user1,
            job=self.job,
            proposal_text="Fast delivery",
            bid_amount=12000.00,
            delivery_days=5,
            status="accepted",
            accepted_at=now
        )
        self.job.status = "in_progress"
        self.job.accepted_at = now
        self.job.expected_completion_date = now + timedelta(days=5)
        self.job.save()

        # Update delivery days to 12
        proposal.delivery_days = 12
        proposal.save()

        self.job.refresh_from_db()
        expected_new_date = now + timedelta(days=12)
        self.assertEqual(self.job.expected_completion_date, expected_new_date)

    def test_auto_deactivate_expired_projects(self):
        """When accepted bid's completion date expires, mark project completed and deactivate."""
        now = timezone.now()
        past_acceptance = now - timedelta(days=10)

        # Job 1: In progress, expired 3 days ago (accepted 10 days ago, 7 day duration)
        proposal_expired = Proposal.objects.create(
            freelancer=self.freelancer_user1,
            job=self.job,
            proposal_text="Expired work",
            bid_amount=10000.00,
            delivery_days=7,
            status="accepted",
            accepted_at=past_acceptance
        )
        self.job.status = "in_progress"
        self.job.is_active = True
        self.job.accepted_at = past_acceptance
        self.job.expected_completion_date = past_acceptance + timedelta(days=7)
        self.job.save()

        # Create an associated payment record to ensure payment status is preserved and not released
        payment = Payment.objects.create(
            client=self.client_user,
            freelancer=self.freelancer_user1,
            proposal=proposal_expired,
            amount=10000.00,
            status="pending",
            paid=False
        )

        # Job 2: Active, unexpired (expires in 5 days)
        job_active = Job.objects.create(
            client=self.client_user,
            title="Ongoing Active Project",
            description="Active unexpired job",
            budget="20000",
            skills="Python",
            experience_level="Intermediate",
            status="in_progress",
            is_active=True,
            accepted_at=now,
            expected_completion_date=now + timedelta(days=5)
        )
        Proposal.objects.create(
            freelancer=self.freelancer_user2,
            job=job_active,
            proposal_text="Ongoing bid",
            bid_amount=20000.00,
            delivery_days=5,
            status="accepted",
            accepted_at=now
        )

        # Execute auto completion service
        processed = auto_complete_expired_projects()
        self.assertEqual(processed, 1)

        # Verify Job 1 is completed and inactive
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "completed")
        self.assertFalse(self.job.is_active)

        # Verify Job 2 remains in_progress and active
        job_active.refresh_from_db()
        self.assertEqual(job_active.status, "in_progress")
        self.assertTrue(job_active.is_active)

        # CRITICAL RULE: Payment record must remain completely untouched
        payment.refresh_from_db()
        self.assertEqual(payment.status, "pending")
        self.assertFalse(payment.paid)

        # Proposal records remain intact
        proposal_expired.refresh_from_db()
        self.assertEqual(proposal_expired.status, "accepted")

    def test_cannot_bid_on_completed_or_inactive_project(self):
        """Verify freelancers cannot submit proposals to completed or inactive jobs."""
        self.job.status = "completed"
        self.job.is_active = False
        self.job.save()

        self.client_http.login(email="free2_exp@example.com", password="password123")
        url = reverse("submit_proposal", args=[self.job.id])

        # Attempt GET
        response = self.client_http.get(url)
        self.assertEqual(response.status_code, 302)

        # Attempt POST
        response = self.client_http.post(url, {
            "proposal_text": "Trying to apply on completed project",
            "bid_amount": "5000",
            "delivery_days": "3"
        })
        self.assertEqual(response.status_code, 302)

        # Verify no proposals created
        self.assertEqual(Proposal.objects.filter(job=self.job).count(), 0)

    def test_inactive_projects_removed_from_search_results(self):
        """Verify completed / inactive jobs are excluded from active search results."""
        self.job.status = "completed"
        self.job.is_active = False
        self.job.save()

        # Create active job
        active_job = Job.objects.create(
            client=self.client_user,
            title="Django Search Target Job",
            description="Searching for Django React developer",
            budget="8000",
            skills="Django, React",
            experience_level="Intermediate",
            status="open",
            is_active=True
        )

        self.client_http.login(email="free1_exp@example.com", password="password123")
        search_url = reverse("freelancer:search_results") + "?q=Django"
        response = self.client_http.get(search_url)

        self.assertEqual(response.status_code, 200)
        jobs_in_context = response.context["projects"]
        job_ids = [j.id for j in jobs_in_context]

        self.assertIn(active_job.id, job_ids)
        self.assertNotIn(self.job.id, job_ids)

    def test_management_command_check_expired_projects(self):
        """Verify check_expired_projects management command runs cleanly and is idempotent."""
        now = timezone.now()
        past = now - timedelta(days=8)
        self.job.status = "in_progress"
        self.job.is_active = True
        self.job.accepted_at = past
        self.job.expected_completion_date = past + timedelta(days=3)
        self.job.save()

        out = io.StringIO()
        call_command("check_expired_projects", stdout=out)
        self.assertIn("1 project(s) marked Completed", out.getvalue())

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "completed")
        self.assertFalse(self.job.is_active)

        # Run second time - idempotent
        out2 = io.StringIO()
        call_command("check_expired_projects", stdout=out2)
        self.assertIn("No expired projects required completion", out2.getvalue())
