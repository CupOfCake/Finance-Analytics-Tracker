from django.db import models

from django.db.models.signals import pre_save, pre_delete, post_save, post_delete
from django.utils.text import slugify
from django.dispatch import receiver
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError


def upload_location(instance: object, filename: str) -> str:
    file_path = 'finance/{user_id}/{transaction_id}-{filename}'.format(
        user_id=str(instance.user.id),
        transaction_id=str(instance.transaction_id),
        filename=filename
    )
    return file_path


class TransactionSplit(models.Model):
    transaction = models.ForeignKey(
        'Transaction',
        on_delete=models.CASCADE,
        related_name='splits'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expense_shares'
    )
    amount = models.IntegerField(
        help_text="Signed amount (e.g., -205 for expense, +150 for refund)."
    )

    class Meta:
        unique_together = [['transaction', 'user']]

    def __str__(self):
        return f"{self.user} share: {self.amount} for {self.transaction}"

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

    def get_split_type(self):
        count = self.splits.count()
        if count == 1:
            return 'me'
        elif count == 2:
            first = self.splits.first()
            last = self.splits.last()
            # Allow difference of 1 (rounding) for 50/50
            if abs(first.amount - last.amount) <= 1:
                return '5050'
            else:
                return 'split'
        else:
            return 'split'

    @staticmethod
    def _format_isk(value):
        """Format an integer as ISK currency string."""
        sign = '-' if value < 0 else ''
        abs_val = abs(int(value))
        formatted = f"{abs_val:,}".replace(',', '.')
        return f"{sign}{formatted} kr."

    def get_split_summary(self):
        """Return a string summary of the split, or None if only one split."""
        splits = self.splits.select_related('user').all()
        if splits.count() <= 1:
            return None

        current_user = self.user
        items = []
        for split in splits:
            if split.user == current_user:
                name = 'me'
            else:
                # Use 4 characters (or full if shorter)
                name = split.user.username[:4] if len(split.user.username) >= 4 else split.user.username
            # Format the amount using the helper
            items.append((name, self._format_isk(split.amount)))

        # Sort: 'me' first, then alphabetically by name
        items.sort(key=lambda x: (x[0] != 'me', x[0]))
        return ' | '.join(f'{name}: {amount}' for name, amount in items)
    
    def __str__(self):
        return super().__str__()


@receiver(post_delete, sender=Transaction)
def submission_delete(sender, instance, *args, **kwargs):
    instance.image.delete(False)

@receiver(post_save, sender=Transaction)
def create_default_split(sender, instance, created, **kwargs):
    if created:
        TransactionSplit.objects.create(
            transaction=instance,
            user=instance.user,
            amount=instance.transaction_ammount
        )

# def pre_save_listing_receiver(sender instance):
#     if not instance.slug:
#         instance.slug = slugify(instance.author.username + '-' + instance.title)
# pre_save.connect(pre_save_listing_receiver, sender=Listing)

# need to add ignore_conflicts=True in the views