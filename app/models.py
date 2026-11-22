from django.db import models
from django.contrib.auth.models import User


class Thumbnail(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="thumbnails"
    )

    filename = models.CharField(max_length=255)
    prompt = models.TextField(blank=True)
    headline = models.CharField(max_length=255, blank=True)
    aspect_ratio = models.CharField(max_length=20, default="16:9")

    created_at = models.DateTimeField(auto_now_add=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.headline or self.filename