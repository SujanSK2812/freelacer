from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from client.models import ClientProfile
from projects.models import Job
from payments.models import Payment

User = get_user_model()

class ClientProfileViewTest(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            email="testclient@example.com",
            username="testclient",
            phone="1234567890",
            role="client",
            password="testpassword"
        )
        self.client_profile = ClientProfile.objects.create(
            user=self.client_user,
            company_name="Acme Global Innovations",
            bio="Innovative solutions for forward-thinking enterprises.",
            website="https://acmeglobal.com",
            city="New York",
            country="USA"
        )
        self.job = Job.objects.create(
            client=self.client_user,
            title="Senior Django Architect",
            description="Looking for an experienced Django architect.",
            budget=5000,
            skills="Django, Python, PostgreSQL",
            experience_level="Expert"
        )

        self.freelancer_user = User.objects.create_user(
            email="testfreelancer@example.com",
            username="testfreelancer",
            phone="0987654321",
            role="freelancer",
            password="testpassword"
        )

    def test_anonymous_user_can_view_client_profile(self):
        url = reverse("accounts:view_profile", kwargs={"user_id": self.client_user.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acme Global Innovations")
        self.assertContains(response, "testclient")
        self.assertContains(response, "Senior Django Architect")
        self.assertContains(response, "5000")
        self.assertContains(response, "New York, USA")
        self.assertFalse(response.context["is_owner"])

    def test_client_owner_sees_management_options(self):
        self.client.login(email="testclient@example.com", password="testpassword")
        url = reverse("accounts:view_profile", kwargs={"user_id": self.client_user.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_owner"])
        self.assertContains(response, "Edit Profile")
        self.assertContains(response, "Post New Job")
        self.assertContains(response, "Delete")

    def test_freelancer_sees_message_and_apply_actions(self):
        self.client.login(email="testfreelancer@example.com", password="testpassword")
        url = reverse("accounts:view_profile", kwargs={"user_id": self.client_user.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_owner"])
        self.assertContains(response, "Message Client")
        self.assertContains(response, "Connect")
        self.assertContains(response, "Submit Proposal")

    def test_client_profile_redirect_to_unified_profile(self):
        self.client.login(email="testclient@example.com", password="testpassword")
        url = reverse("client:client_profile")
        response = self.client.get(url)
        self.assertRedirects(response, reverse("accounts:view_profile", kwargs={"user_id": self.client_user.id}))

    def test_share_profile_widget_is_removed(self):
        url = reverse("accounts:view_profile", kwargs={"user_id": self.client_user.id})
        response = self.client.get(url)
        self.assertNotContains(response, "Share Profile")
        self.assertNotContains(response, "Copy Profile Link")

    def test_owner_sees_add_banner_option(self):
        self.client.login(email="testclient@example.com", password="testpassword")
        url = reverse("accounts:view_profile", kwargs={"user_id": self.client_user.id})
        response = self.client.get(url)
        self.assertContains(response, "Add Banner")
        self.assertContains(response, "bannerModalBackdrop")

    def test_banner_upload_and_removal(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        import io

        self.client.login(email="testclient@example.com", password="testpassword")
        
        # Create small test image
        img_io = io.BytesIO()
        image = Image.new("RGB", (300, 100), color=(73, 109, 137))
        image.save(img_io, format="JPEG")
        test_file = SimpleUploadedFile("test_banner.jpg", img_io.getvalue(), content_type="image/jpeg")

        upload_url = reverse("client:update_client_banner")
        response = self.client.post(upload_url, {"banner_image": test_file})
        self.assertRedirects(response, reverse("accounts:view_profile", kwargs={"user_id": self.client_user.id}))

        self.client_profile.refresh_from_db()
        self.assertTrue(self.client_profile.banner_image)

        # Profile view now shows Change Banner
        profile_url = reverse("accounts:view_profile", kwargs={"user_id": self.client_user.id})
        resp = self.client.get(profile_url)
        self.assertContains(resp, "Change Banner")
        self.assertContains(resp, "has-banner")

        # Test removal
        remove_response = self.client.post(upload_url, {"action": "delete"})
        self.assertRedirects(remove_response, profile_url)
        self.client_profile.refresh_from_db()
        self.assertFalse(self.client_profile.banner_image)


class TestimonialOnePerUserTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="author@example.com",
            username="TestAuthor2812",
            phone="1122334455",
            role="freelancer",
            password="testpassword"
        )

    def test_user_can_submit_first_testimonial(self):
        from accounts.models import Testimonial
        self.client.login(email="author@example.com", password="testpassword")
        url = reverse("accounts:testimonials")

        # Initial view shows submission form
        resp = self.client.get(url)
        self.assertContains(resp, "Add Your Testimonial")
        self.assertFalse(resp.context["user_has_testimonial"])

        # Submit testimonial
        post_resp = self.client.post(url, {
            "rating": "5",
            "message": "Outstanding freelancing platform experience!"
        })
        self.assertRedirects(post_resp, url)
        self.assertEqual(Testimonial.objects.filter(user=self.user).count(), 1)

    def test_user_cannot_submit_duplicate_testimonial(self):
        from accounts.models import Testimonial
        # Create an existing testimonial for this user
        Testimonial.objects.create(
            user=self.user,
            name="TestAuthor2812",
            role="Freelancer",
            rating=5,
            message="My first and only review."
        )

        self.client.login(email="author@example.com", password="testpassword")
        url = reverse("accounts:testimonials")

        # GET request: Form is hidden, published card is shown
        resp = self.client.get(url)
        self.assertTrue(resp.context["user_has_testimonial"])
        self.assertContains(resp, "Your Testimonial is Published")
        self.assertNotContains(resp, 'id="submit-form-section"')
        self.assertContains(resp, "My first and only review.")

        # Attempt second submission via POST: Should be rejected and not create second record
        post_resp = self.client.post(url, {
            "rating": "4",
            "message": "Attempting second review."
        })
        self.assertRedirects(post_resp, url)
        self.assertEqual(Testimonial.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Testimonial.objects.filter(message="Attempting second review.").count(), 0)
