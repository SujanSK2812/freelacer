from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from projects.models import JobPost, Comment, Reaction, CommentReaction

User = get_user_model()


class SocialActionsTestCase(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client_test",
            email="client_test@example.com",
            phone="1112223334",
            password="Password123!",
            role="client"
        )
        self.freelancer_user = User.objects.create_user(
            username="freelancer_test",
            email="freelancer_test@example.com",
            phone="1112223335",
            password="Password123!",
            role="freelancer"
        )
        self.post = JobPost.objects.create(
            client=self.freelancer_user,
            title="Backend Showcase",
            description="Django REST APIs"
        )

    def test_client_likes_post_ajax(self):
        c = Client()
        c.force_login(self.client_user)

        # 1. Like post
        resp = c.get(f"/projects/like/{self.post.id}/?ajax=true", HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['liked'])
        self.assertEqual(data['likes_count'], 1)
        self.assertTrue(Reaction.objects.filter(job=self.post, user=self.client_user, reaction_type='like').exists())

        # 2. Unlike post
        resp2 = c.get(f"/projects/like/{self.post.id}/?ajax=true", HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertFalse(data2['liked'])
        self.assertEqual(data2['likes_count'], 0)

    def test_client_comments_and_replies_ajax(self):
        c = Client()
        c.force_login(self.client_user)

        # 1. Post a comment
        resp = c.post(
            f"/projects/comment/{self.post.id}/",
            {"comment": "Impressive portfolio!", "ajax": "true"},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['text'], "Impressive portfolio!")
        self.assertEqual(data['comments_count'], 1)
        comment_id = data['comment_id']

        # 2. Freelancer replies to comment
        c_fl = Client()
        c_fl.force_login(self.freelancer_user)
        resp_reply = c_fl.post(
            f"/projects/comment/{self.post.id}/",
            {"comment": "Thank you!", "parent_id": comment_id, "ajax": "true"},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp_reply.status_code, 200)
        data_reply = resp_reply.json()
        self.assertTrue(data_reply['success'])
        self.assertEqual(data_reply['parent_id'], comment_id)

        # 3. Client reacts to the comment
        resp_reaction = c.get(
            f"/projects/comment-reaction/{comment_id}/?ajax=true",
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp_reaction.status_code, 200)
        self.assertTrue(resp_reaction.json()['liked'])
        self.assertEqual(resp_reaction.json()['likes_count'], 1)

    def test_client_home_renders_social_actions(self):
        c = Client()
        c.force_login(self.client_user)
        resp = c.get("/client/home/")
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        # Verify like button and comment button exist
        self.assertIn(f"toggleLikePost(this, {self.post.id})", content)
        self.assertIn(f"toggleComments('comments-box-{self.post.id}')", content)
        self.assertIn(f"comments-box-{self.post.id}", content)
