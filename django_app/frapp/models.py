from django.db import models
from django.contrib.auth.models import User


class Docs(models.Model):
    id = models.AutoField(primary_key=True)
    file_path = models.FileField(upload_to='documents/')
    size = models.PositiveIntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.file_path:
            self.size = self.file_path.size
        super().save(*args, **kwargs)


class Users_To_Docs(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=63)
    docs_id = models.ForeignKey(Docs, on_delete=models.CASCADE, related_name='users_to_docs')


class Price(models.Model):
    id = models.AutoField(primary_key=True)
    file_type = models.CharField(max_length=7)
    price = models.FloatField()


class Cart(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart')
    docs_id = models.ForeignKey(Docs, on_delete=models.CASCADE, related_name='cart')
    order_price = models.FloatField()
    payment = models.BooleanField(default=False)

