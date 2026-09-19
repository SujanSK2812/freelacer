from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.template import Template, Context
from projects.models import Job, JobPost, Comment, Reaction

User = get_user_model()


class PostInteractionUITestCase(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client_test_user",
            email="client_test_user@example.com",
            phone="9876543210",
            password="Password123!",
            role="client"
        )
        self.freelancer_user = User.objects.create_user(
            username="freelancer_test_user",
            email="freelancer_test_user@example.com",
            phone="9876543211",
            password="Password123!",
            role="freelancer"
        )
        self.client_job = Job.objects.create(
            client=self.client_user,
            title="Frontend React UI",
            description="Need clean UI",
            budget="$500",
            skills="React, CSS",
            experience_level="Intermediate"
        )
        self.post = JobPost.objects.create(
            client=self.freelancer_user,
            title="Design Portfolio Showcase",
            description="Full-stack Showcase"
        )

    def test_pluralization_rules(self):
        """Test the exact singular/plural counts requested by user."""
        template_str = "{{ count }} {{ count|pluralize:'Like,Likes' }} / {{ count }} {{ count|pluralize:'Comment,Comments' }}"
        t = Template(template_str)

        # 0 likes & 0 comments
        res_0 = t.render(Context({'count': 0}))
        self.assertEqual(res_0, "0 Likes / 0 Comments")

        # 1 like & 1 comment
        res_1 = t.render(Context({'count': 1}))
        self.assertEqual(res_1, "1 Like / 1 Comment")

        # 2 likes & 2 comments
        res_2 = t.render(Context({'count': 2}))
        self.assertEqual(res_2, "2 Likes / 2 Comments")

        # 5 likes & 5 comments
        res_5 = t.render(Context({'count': 5}))
        self.assertEqual(res_5, "5 Likes / 5 Comments")

    def test_freelancer_home_post_interaction_elements(self):
        c = Client()
        c.force_login(self.freelancer_user)
        resp = c.get("/freelancer/home/")
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode('utf-8')

        # Verify exact interactive count containers exist
        self.assertIn(f'id="job-likes-count-{self.client_job.id}"', html)
        self.assertIn(f'id="job-comments-count-{self.client_job.id}"', html)
        self.assertIn(f'id="likes-count-{self.post.id}"', html)
        self.assertIn(f'id="comments-count-{self.post.id}"', html)

        # Initial counts should be "0 Likes" and "0 Comments"
        self.assertIn("0 Likes", html)
        self.assertIn("0 Comments", html)

        # Crucial check: Ensure NO duplicate action buttons like "Liked" button or separate "Comment" button
        self.assertNotIn('>Liked<', html)
        self.assertNotIn('>Comment<', html)

    def test_client_home_post_interaction_elements(self):
        c = Client()
        c.force_login(self.client_user)
        resp = c.get("/client/home/")
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode('utf-8')

        # Verify exact interactive count containers exist
        self.assertIn(f'id="job-likes-count-{self.client_job.id}"', html)
        self.assertIn(f'id="job-comments-count-{self.client_job.id}"', html)
        self.assertIn(f'id="likes-count-{self.post.id}"', html)
        self.assertIn(f'id="comments-count-{self.post.id}"', html)

        # Initial counts should be "0 Likes" and "0 Comments"
        self.assertIn("0 Likes", html)
        self.assertIn("0 Comments", html)

        # Crucial check: Ensure NO duplicate action buttons like "Liked" button or separate "Comment" button
        self.assertNotIn('>Liked<', html)
        self.assertNotIn('>Comment<', html)

    def test_like_unlike_toggle_live_count(self):
        c = Client()
        c.force_login(self.freelancer_user)

        # 1. Like job
        resp = c.get(f"/projects/like-job/{self.client_job.id}/?ajax=true", HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['liked'])
        self.assertEqual(data['likes_count'], 1)

        # Re-fetch freelancer home to check rendered HTML reflects 1 Like
        resp_home = c.get("/freelancer/home/")
        html_home = resp_home.content.decode('utf-8')
        self.assertIn("1 Like", html_home)
        self.assertNotIn('>Liked<', html_home)

        # 2. Unlike job
        resp2 = c.get(f"/projects/like-job/{self.client_job.id}/?ajax=true", HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertFalse(data2['liked'])
        self.assertEqual(data2['likes_count'], 0)

        # Re-fetch freelancer home to check rendered HTML reflects 0 Likes
        resp_home2 = c.get("/freelancer/home/")
        html_home2 = resp_home2.content.decode('utf-8')
        self.assertIn("0 Likes", html_home2)

    def test_multiple_likes_and_comments_rendered(self):
        """Test posts with multiple (5) likes and multiple (5) comments."""
        # Create 5 users to like and comment
        for i in range(5):
            u = User.objects.create_user(
                username=f"user_{i}",
                email=f"user_{i}@example.com",
                phone=f"900000000{i}",
                password="Password123!",
                role="freelancer"
            )
            Reaction.objects.create(user=u, client_job=self.client_job, reaction_type="like")
            Comment.objects.create(user=u, client_job=self.client_job, text=f"Comment number {i}")

        c = Client()
        c.force_login(self.freelancer_user)
        resp = c.get("/freelancer/home/")
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode('utf-8')

        # Should render 5 Likes and 5 Comments
        self.assertIn("5 Likes", html)
        self.assertIn("5 Comments", html)
        # Should not have duplicate button text
        self.assertNotIn('>Liked<', html)
        self.assertNotIn('>Comment<', html)
