from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
# Create your models here.

class GMTPlus1DateTimeField(models.DateTimeField):
    def pre_save(self, model_instance, add):
        value = timezone.now() + timezone.timedelta(hours=1)
        setattr(model_instance, self.attname, value)
        return value
    
class UploadedFile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)  # Store the filename
    uploaded_at = GMTPlus1DateTimeField()

    def __str__(self):
        return self.filename
        