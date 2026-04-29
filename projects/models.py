from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


# ===============================
# LinkedIn Style Job Post
# ===============================

class JobPost(models.Model):

    client = models.ForeignKey(User, on_delete=models.CASCADE)

    title = models.CharField(max_length=200)

    description = models.TextField()

    image = models.ImageField(upload_to="job_images/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # Count reactions
    def total_reactions(self):
        return self.reactions.count()

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
        on_delete=models.CASCADE
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
        on_delete=models.CASCADE
    )

    text = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user}"


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

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title