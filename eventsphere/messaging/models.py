from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Conversation(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    participants = models.ManyToManyField(User, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.name:
            return self.name
        return "Chat: " + ", ".join([u.username for u in self.participants.all()])

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

class ConversationNickname(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="nicknames")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=50)

    class Meta:
        unique_together = ("conversation", "user")

    def __str__(self):
        return f"{self.user.username} → {self.nickname}"

class MessageRead(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reads")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user')