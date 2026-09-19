from django.db import models
from django.conf import settings
from freelancer_portal.upload_utils import (
    SafeImageField,
    client_job_path,
    client_poster_path,
    freelancer_talent_path,
    freelancer_poster_path,
)

User = settings.AUTH_USER_MODEL


# ===============================
# LinkedIn Style Job Post
# ===============================

class JobPost(models.Model):

    client = models.ForeignKey(User, on_delete=models.CASCADE)

    title = models.CharField(max_length=200)

    description = models.TextField()

    image = SafeImageField(upload_to=freelancer_talent_path, blank=True, null=True)
    poster = SafeImageField(upload_to=freelancer_poster_path, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # Count reactions
    def total_reactions(self):
        return self.reactions.count()

    def total_likes(self):
        return self.reactions.filter(reaction_type="like").count()

    def __str__(self):
        return self.title


class Reaction(models.Model):

    REACTION_CHOICES = [
        ("like", "Like"),
        ("love", "Love"),
        ("clap", "Clap"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    job = models.ForeignKey(
        JobPost,
        related_name="reactions",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    client_job = models.ForeignKey(
        'Job',
        related_name="reactions",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    reaction_type = models.CharField(
        max_length=10,
        choices=REACTION_CHOICES
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} reacted {self.reaction_type}"


class Comment(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    job = models.ForeignKey(
        JobPost,
        related_name="comments",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    client_job = models.ForeignKey(
        'Job',
        related_name="comments",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    text = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)

    def total_likes(self):
        return self.reactions.filter(reaction_type="like").count()

    def __str__(self):
        return f"Comment by {self.user}"


class CommentReaction(models.Model):

    REACTION_CHOICES = [
        ("like", "Like"),
        ("love", "Love"),
        ("clap", "Clap"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    comment = models.ForeignKey(
        Comment,
        related_name="reactions",
        on_delete=models.CASCADE
    )

    reaction_type = models.CharField(
        max_length=10,
        choices=REACTION_CHOICES
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} reacted {self.reaction_type} on comment"


# ===============================
# Freelancer Job Listing
# ===============================

class Job(models.Model):

    client = models.ForeignKey(User, on_delete=models.CASCADE)

    title = models.CharField(max_length=200)

    description = models.TextField()

    budget = models.CharField(max_length=100)

    skills = models.CharField(max_length=200)

    experience_level = models.CharField(max_length=50)

    image = SafeImageField(upload_to=client_job_path, blank=True, null=True)
    poster = SafeImageField(upload_to=client_poster_path, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # Count reactions
    def total_reactions(self):
        return self.reactions.count()

    def total_likes(self):
        return self.reactions.filter(reaction_type="like").count()

    @property
    def has_accepted_proposal(self):
        return self.job_proposals.filter(status="accepted").exists()

    def __str__(self):
        return self.title