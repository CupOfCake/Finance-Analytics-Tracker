from django.db import models

from django.db.models.signals import pre_save, pre_delete, post_delete
from django.utils.text import slugify
from django.dispatch import receiver
from django.conf import settings



def upload_location(instance: object, filename: str) -> str:
    file_path = 'finance/{user_id}/{transaction_id}-{filename}'.format(
        user_id=str(instance.user.id),
        transaction_id=str(instance.transaction_id),
        filename=filename
    )
    return file_path

class Transaction(models.Model):
    # need to give author id to match transaction to user.
    user                = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # bare minimum required to catagorise transactions
    transaction_id      = models.IntegerField(null=False, blank=False)
    transaction_date    = models.DateTimeField(null=False, blank=False)
    transaction_ammount = models.IntegerField(null=False, blank=False)
    transaction_name    = models.CharField(max_length=50, null=False, blank=False)
    transaction_type    = models.CharField(max_length=50, null=False, blank=False)

    #additional info added to transaction, note and image
    transaction_note    = models.TextField(max_length=2000, null=True, blank=True)
    image               = models.ImageField(upload_to=upload_location, null=True, blank=True)

    # info on when data was added or altered
    date_published      = models.DateTimeField(auto_now_add=True, verbose_name="date published")
    date_updated        = models.DateTimeField(auto_now=True, verbose_name="date updated")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'transaction_id', 'transaction_date'],
                name='unique_user_transaction_per_date'
            )
        ]


    def __str__(self):
        return super().__str__()

@receiver(post_delete, sender=Transaction)
def submission_delete(sender, instance, *args, **kwargs):
    instance.image.delete(False)

# def pre_save_listing_receiver(sender instance):
#     if not instance.slug:
#         instance.slug = slugify(instance.author.username + '-' + instance.title)
# pre_save.connect(pre_save_listing_receiver, sender=Listing)

# need to add ignore_conflicts=True in the views