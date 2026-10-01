import io
from PIL import Image
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from freelancer.models import FreelancerProfile

User = get_user_model()


class FreelancerBannerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testfreelancer",
            email="testfreelancer@example.com",
            password="testpassword123",
            role="freelancer",
        )
        self.profile, _ = FreelancerProfile.objects.get_or_create(user=self.user)
        self.client.login(email="testfreelancer@example.com", password="testpassword123")

    def _create_test_image(self, name="banner.jpg"):
        img_io = io.BytesIO()
        image = Image.new("RGB", (600, 200), color=(10, 102, 194))
        image.save(img_io, format="JPEG")
        return SimpleUploadedFile(name, img_io.getvalue(), content_type="image/jpeg")

    def test_create_profile_banner_upload_and_removal(self):
        # 1. Test upload banner via create_profile
        test_file = self._create_test_image("profile_banner.jpg")
        url = reverse("freelancer:create_profile")
        response = self.client.post(url, {
            "title": "Full Stack Dev",
            "bio": "Experienced Python developer",
            "experience_level": "expert",
            "hourly_rate": "75.00",
            "banner_image": test_file,
        })
        self.assertEqual(response.status_code, 302)

        self.profile.refresh_from_db()
        self.assertTrue(bool(self.profile.banner_image))
        self.assertIn("uploads/freelancers/banner/", str(self.profile.banner_image))

        # Check User.get_banner_image property
        self.assertIsNotNone(self.user.get_banner_image)

        # 2. Verify banner renders on public freelancer profile
        profile_url = reverse("freelancer:freelancer_profile", kwargs={"freelancer_id": self.user.id})
        profile_resp = self.client.get(profile_url)
        self.assertEqual(profile_resp.status_code, 200)
        self.assertContains(profile_resp, "has-custom-banner")
        self.assertContains(profile_resp, self.profile.banner_image.url)

        # 3. Test remove banner via create_profile
        remove_resp = self.client.post(url, {
            "title": "Full Stack Dev",
            "bio": "Experienced Python developer",
            "remove_banner_image": "1",
        })
        self.assertEqual(remove_resp.status_code, 302)
        self.profile.refresh_from_db()
        self.assertFalse(bool(self.profile.banner_image))

    def test_edit_profile_banner_upload_and_removal(self):
        test_file = self._create_test_image("edit_banner.jpg")
        url = reverse("freelancer:edit_profile")
        response = self.client.post(url, {
            "username": "testfreelancer",
            "first_name": "John",
            "last_name": "Doe",
            "banner_image": test_file,
        })
        self.assertEqual(response.status_code, 302)
        self.profile.refresh_from_db()
        self.assertTrue(bool(self.profile.banner_image))

        # Remove banner
        response = self.client.post(url, {
            "username": "testfreelancer",
            "first_name": "John",
            "last_name": "Doe",
            "remove_banner_image": "1",
        })
        self.assertEqual(response.status_code, 302)
        self.profile.refresh_from_db()
        self.assertFalse(bool(self.profile.banner_image))

    def test_update_freelancer_banner_view(self):
        test_file = self._create_test_image("direct_banner.jpg")
        url = reverse("freelancer:update_freelancer_banner")
        response = self.client.post(url, {"banner_image": test_file})
        self.assertEqual(response.status_code, 302)
        self.profile.refresh_from_db()
        self.assertTrue(bool(self.profile.banner_image))

        # Delete action
        del_resp = self.client.post(url, {"action": "delete"})
        self.assertEqual(del_resp.status_code, 302)
        self.profile.refresh_from_db()
        self.assertFalse(bool(self.profile.banner_image))
