from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='')
    campus_block = models.CharField(max_length=100, default='Kumari Hall', blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"
