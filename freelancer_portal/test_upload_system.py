import io
import os
import shutil
from pathlib import Path
from PIL import Image

from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.conf import settings

from client.models import ClientProfile
from freelancer.models import FreelancerProfile
from projects.models import Job, JobPost
from freelancer_portal.upload_utils import (
    validate_uploaded_image,
    safe_delete_unreferenced_file,
    SafeImageFieldFile,
)

User = get_user_model()


def generate_test_image(filename="test.png", format="PNG", size=(100, 100), color="blue"):
    """Helper to generate in-memory dummy image file."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    buf.seek(0)
    mime = "image/png" if format.upper() == "PNG" else "image/jpeg"
    return SimpleUploadedFile(filename, buf.read(), content_type=mime)


class UploadSystemTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client_user",
            email="client@test.com",
            phone="9876543210",
            password="Password123!",
            role="client"
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.freelancer_user = User.objects.create_user(
            username="freelancer_user",
            email="freelancer@test.com",
            phone="9876543211",
            password="Password123!",
            role="freelancer"
        )
        self.freelancer_profile = FreelancerProfile.objects.create(user=self.freelancer_user)

        self.other_client = User.objects.create_user(
            username="other_client",
            email="other@test.com",
            phone="9876543212",
            password="Password123!",
            role="client"
        )
        self.created_files = []

    def tearDown(self):
        # Clean up any files created during tests
        for f in self.created_files:
            abs_p = Path(settings.BASE_DIR) / f
            if abs_p.is_file():
                try:
                    abs_p.unlink()
                except Exception:
                    pass

    def test_client_profile_picture_upload(self):
        """1. Client uploads profile image -> saved in uploads/clients/profile/ with relative DB path."""
        c = Client()
        c.force_login(self.client_user)

        test_img = generate_test_image("avatar.jpg", format="JPEG")
        response = c.post(
            "/client/edit-profile/",
            {
                "company_name": "TestCorp",
                "bio": "Client bio",
                "website": "https://testcorp.com",
                "country": "India",
                "city": "Bangalore",
                "profile_picture": test_img,
            },
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        self.client_profile.refresh_from_db()
        self.assertTrue(self.client_profile.profile_picture)
        name = self.client_profile.profile_picture.name
        self.created_files.append(name)

        # Check relative path in database
        self.assertTrue(name.startswith("uploads/clients/profile/"))
        self.assertNotIn("/Users/", name)

        # Check physical file exists
        abs_path = Path(settings.BASE_DIR) / name
        self.assertTrue(abs_path.is_file())

        # Check URL resolution
        self.assertEqual(self.client_profile.profile_picture.url, f"/{name}")

    def test_client_job_and_poster_upload(self):
        """2. Client creates job with image and poster -> stored in uploads/clients/jobs/ and posters/."""
        c = Client()
        c.force_login(self.client_user)

        job_img = generate_test_image("job_banner.png", format="PNG")
        job_poster = generate_test_image("job_poster.jpg", format="JPEG")

        response = c.post(
            "/client/create-job/",
            {
                "title": "Full Stack Django Developer",
                "description": "Build high quality scalable web applications",
                "budget": "25000",
                "skills": "Python, Django, React",
                "experience_level": "Expert",
                "image": job_img,
                "poster": job_poster,
            },
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        job = Job.objects.filter(client=self.client_user, title="Full Stack Django Developer").first()
        self.assertIsNotNone(job)
        self.assertTrue(job.image)
        self.assertTrue(job.poster)

        img_name = job.image.name
        poster_name = job.poster.name
        self.created_files.extend([img_name, poster_name])

        # Verify relative paths
        self.assertTrue(img_name.startswith("uploads/clients/jobs/"))
        self.assertTrue(poster_name.startswith("uploads/clients/posters/"))

        # Verify physical files
        self.assertTrue((Path(settings.BASE_DIR) / img_name).is_file())
        self.assertTrue((Path(settings.BASE_DIR) / poster_name).is_file())

    def test_freelancer_profile_upload(self):
        """3. Freelancer uploads profile image -> saved in uploads/freelancers/profile/."""
        c = Client()
        c.force_login(self.freelancer_user)

        fl_avatar = generate_test_image("fl_avatar.png", format="PNG")
        response = c.post(
            "/freelancer/create_profile/",
            {
                "title": "Senior Python Architect",
                "bio": "Building reliable systems",
                "skills": "Python, FastAPI, Django",
                "profile_picture": fl_avatar,
            },
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        self.freelancer_profile.refresh_from_db()
        self.assertTrue(self.freelancer_profile.profile_picture)
        name = self.freelancer_profile.profile_picture.name
        self.created_files.append(name)

        self.assertTrue(name.startswith("uploads/freelancers/profile/"))
        self.assertTrue((Path(settings.BASE_DIR) / name).is_file())

    def test_freelancer_showcase_and_poster(self):
        """4. Freelancer creates talent showcase -> saved in uploads/freelancers/talents/ & posters/."""
        c = Client()
        c.force_login(self.freelancer_user)

        showcase_img = generate_test_image("showcase.png", format="PNG")
        showcase_poster = generate_test_image("showcase_poster.jpg", format="JPEG")

        response = c.post(
            "/freelancer/create-showcase/",
            {
                "title": "Cloud Native Microservices",
                "description": "High throughput microservices using Django and Docker",
                "image": showcase_img,
                "poster": showcase_poster,
            },
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        showcase = JobPost.objects.filter(client=self.freelancer_user, title="Cloud Native Microservices").first()
        self.assertIsNotNone(showcase)
        self.assertTrue(showcase.image)
        self.assertTrue(showcase.poster)

        img_name = showcase.image.name
        poster_name = showcase.poster.name
        self.created_files.extend([img_name, poster_name])

        self.assertTrue(img_name.startswith("uploads/freelancers/talents/"))
        self.assertTrue(poster_name.startswith("uploads/freelancers/posters/"))
        self.assertTrue((Path(settings.BASE_DIR) / img_name).is_file())
        self.assertTrue((Path(settings.BASE_DIR) / poster_name).is_file())

    def test_validation_rejects_non_image_files(self):
        """Validate that non-image and executable files are rejected."""
        fake_exe = SimpleUploadedFile("malware.exe", b"MZ\x90\x00not an image", content_type="application/octet-stream")
        with self.assertRaises(ValidationError):
            validate_uploaded_image(fake_exe)

        fake_png = SimpleUploadedFile("fake.png", b"This is plain text pretending to be png", content_type="image/png")
        with self.assertRaises(ValidationError):
            validate_uploaded_image(fake_png)

    def test_safe_delete_unreferenced_file_and_preserves_referenced(self):
        """Delete file when unreferenced, but preserve when referenced by another record."""
        # Create a real file on disk
        img_name = "uploads/clients/jobs/shared_test.png"
        abs_path = Path(settings.BASE_DIR) / img_name
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (50, 50), color="green")
        img.save(str(abs_path), format="PNG")
        self.created_files.append(img_name)

        # Create two jobs pointing to this same file
        job1 = Job.objects.create(
            client=self.client_user,
            title="Job 1",
            description="First job",
            budget="100",
            image=img_name
        )
        job2 = Job.objects.create(
            client=self.client_user,
            title="Job 2",
            description="Second job",
            budget="200",
            image=img_name
        )

        # Try to delete file while job2 still references it -> should NOT delete physical file
        deleted = safe_delete_unreferenced_file(img_name)
        self.assertFalse(deleted)
        self.assertTrue(abs_path.is_file(), "File must not be deleted while referenced by job2")

        # Now remove job2 reference
        job2.image = ""
        job2.save()
        job1.image = ""
        job1.save()

        # Now neither references it -> safe to delete
        deleted = safe_delete_unreferenced_file(img_name)
        self.assertTrue(deleted)
        self.assertFalse(abs_path.is_file(), "File should be deleted once unreferenced")

    def test_missing_physical_file_graceful_handling(self):
        """Missing physical file should not cause broken images or 500 errors."""
        missing_rel = "uploads/clients/jobs/nonexistent_file_xyz.png"
        job = Job.objects.create(
            client=self.client_user,
            title="Job With Missing File",
            description="Description",
            budget="500",
            image=missing_rel
        )

        # SafeImageFieldFile evaluates to False when physical file is missing
        self.assertFalse(bool(job.image))
        self.assertEqual(job.image.url, "")
        self.assertEqual(job.image.name, missing_rel)

    def test_ownership_enforcement_on_deletion(self):
        """Clients can only delete their own jobs; freelancers can only delete their own showcases."""
        client_job = Job.objects.create(
            client=self.client_user,
            title="Private Job",
            description="Desc",
            budget="500"
        )

        # Freelancer tries to delete client's job
        c = Client()
        c.force_login(self.freelancer_user)
        resp = c.post(f"/client/delete-job/{client_job.id}/")
        # Should be redirected or 403 / forbidden / 404
        self.assertTrue(Job.objects.filter(id=client_job.id).exists())

        # Other client tries to delete client's job
        c.force_login(self.other_client)
        resp = c.post(f"/client/delete-job/{client_job.id}/")
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Job.objects.filter(id=client_job.id).exists())

        # Owner client can delete it
        c.force_login(self.client_user)
        resp = c.post(f"/client/delete-job/{client_job.id}/", follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Job.objects.filter(id=client_job.id).exists())
