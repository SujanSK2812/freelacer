from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from projects.models import Job, JobPost
import json

User = get_user_model()


class PostUploadNavigationTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="test_client",
            email="client@example.com",
            phone="1111111111",
            password="Password123!",
            role="client"
        )
        self.freelancer_user = User.objects.create_user(
            username="test_freelancer",
            email="freelancer@example.com",
            phone="2222222222",
            password="Password123!",
            role="freelancer"
        )

    def test_client_post_upload_ajax(self):
        """Verify client post upload via AJAX returns 200, success message, and redirect to client_home."""
        c = Client()
        c.force_login(self.client_user)

        response = c.post(
            reverse("client:create_job"),
            {
                "title": "Build a Django Web Portal",
                "description": "Looking for a seasoned backend engineer.",
                "budget": "15000",
                "skills": "Python, Django",
                "experience_level": "Expert"
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["message"], "Post uploaded successfully!")
        self.assertEqual(data["redirect_url"], reverse("client:client_home"))

        # Verify database record
        job = Job.objects.filter(client=self.client_user, title="Build a Django Web Portal").first()
        self.assertIsNotNone(job)
        self.assertEqual(job.budget, "15000")

        # Verify post appears in client's feed section
        feed_response = c.get(data["redirect_url"])
        self.assertEqual(feed_response.status_code, 200)
        self.assertContains(feed_response, "Build a Django Web Portal")
        self.assertContains(feed_response, "test_client")

    def test_client_post_upload_standard_redirect(self):
        """Verify standard form submission redirects to client_home instead of root '/'."""
        c = Client()
        c.force_login(self.client_user)

        response = c.post(
            reverse("client:create_job"),
            {
                "title": "Mobile App UI Overhaul",
                "description": "Figma to Flutter design implementation.",
                "budget": "8000",
                "skills": "Flutter, Dart",
                "experience_level": "Intermediate"
            }
        )

        self.assertRedirects(response, reverse("client:client_home"))

    def test_client_post_upload_validation_error(self):
        """Verify upload fails without title or description and returns 400 error."""
        c = Client()
        c.force_login(self.client_user)

        response = c.post(
            reverse("client:create_job"),
            {
                "title": "",
                "description": "",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("job title and description", data["message"])

    def test_client_post_duplicate_prevention(self):
        """Verify duplicate posts are prevented when submitted in quick succession."""
        c = Client()
        c.force_login(self.client_user)

        post_data = {
            "title": "Unique Job Title",
            "description": "Job details description.",
            "budget": "5000",
            "skills": "Python",
            "experience_level": "Intermediate"
        }

        # First submission
        resp1 = c.post(reverse("client:create_job"), post_data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp1.status_code, 200)

        # Immediate duplicate submission
        resp2 = c.post(reverse("client:create_job"), post_data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp2.status_code, 200)

        # Count in DB should be exactly 1
        self.assertEqual(Job.objects.filter(client=self.client_user, title="Unique Job Title").count(), 1)

    def test_freelancer_showcase_upload_ajax(self):
        """Verify freelancer showcase upload via AJAX returns 200, success message, and redirect to freelancer_home with tab=freelancer-posts."""
        c = Client()
        c.force_login(self.freelancer_user)

        response = c.post(
            reverse("freelancer:create_showcase"),
            {
                "title": "Full Stack React and Django Portfolio Showcase",
                "description": "5+ years building scalable SaaS applications."
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["message"], "Post uploaded successfully!")
        expected_url = reverse("freelancer:freelancer_home") + "?tab=freelancer-posts"
        self.assertEqual(data["redirect_url"], expected_url)

        # Verify database record
        showcase = JobPost.objects.filter(client=self.freelancer_user, title="Full Stack React and Django Portfolio Showcase").first()
        self.assertIsNotNone(showcase)

        # Verify post appears in freelancer's feed section
        feed_response = c.get(data["redirect_url"])
        self.assertEqual(feed_response.status_code, 200)
        self.assertContains(feed_response, "Full Stack React and Django Portfolio Showcase")
        self.assertContains(feed_response, "test_freelancer")

    def test_freelancer_showcase_upload_standard_redirect(self):
        """Verify standard form submission redirects to freelancer_home?tab=freelancer-posts instead of root '/'."""
        c = Client()
        c.force_login(self.freelancer_user)

        response = c.post(
            reverse("freelancer:create_showcase"),
            {
                "title": "Cloud Architecture Showcase",
                "description": "AWS / Kubernetes microservices portfolio."
            }
        )

        expected_url = reverse("freelancer:freelancer_home") + "?tab=freelancer-posts"
        self.assertRedirects(response, expected_url)

    def test_freelancer_showcase_validation_error(self):
        """Verify upload fails without title or description and returns 400 error."""
        c = Client()
        c.force_login(self.freelancer_user)

        response = c.post(
            reverse("freelancer:create_showcase"),
            {
                "title": "",
                "description": "",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["status"], "error")

    def test_freelancer_showcase_duplicate_prevention(self):
        """Verify duplicate posts are prevented when submitted multiple times."""
        c = Client()
        c.force_login(self.freelancer_user)

        post_data = {
            "title": "Duplicate Showcase Check",
            "description": "Showcase description."
        }

        resp1 = c.post(reverse("freelancer:create_showcase"), post_data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp1.status_code, 200)

        resp2 = c.post(reverse("freelancer:create_showcase"), post_data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp2.status_code, 200)

        self.assertEqual(JobPost.objects.filter(client=self.freelancer_user, title="Duplicate Showcase Check").count(), 1)
