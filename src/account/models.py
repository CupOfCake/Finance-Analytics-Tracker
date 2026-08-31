from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.conf import settings


class MyAccountManager(BaseUserManager):
    def create_user(self, email, username, password=None):
        if not email:
            raise ValueError("Users must have an email address")
        if not username:
            raise ValueError("Users must have a username")

        user = self.model(
            email=self.normalize_email(email),
            username=username,
        )

        user.set_password(password)
        user.save(using=self._db)
        return user
    

    def create_superuser(self, email, username, password):
        user = self.create_user(
            email=self.normalize_email(email),
            password=password,
            username=username,
        )
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user
    

# handle file upload location for profile images
def profile_upload_location(instance: models.Model, filename: str) -> str:
    if isinstance(instance, Account):
        
        file_path = 'account/{author_id}/{filename}-{filename}'.format(
            author_id=str(instance.id), 
            title=str(instance.username),
            filename=filename
        )
        return file_path
    else:
        return 'account/{filename}'.format(filename=filename)

class Account(AbstractBaseUser):
    email           = models.EmailField(verbose_name='email', max_length=60, unique=True)
    profile_pic         = models.ImageField(upload_to=profile_upload_location, null=True, blank=True)
    username        = models.CharField(max_length=30, unique=True)
    date_joined     = models.DateTimeField(verbose_name='date joined', auto_now_add=True)
    last_login      = models.DateTimeField(verbose_name='last login', auto_now=True)
    is_admin        = models.BooleanField(default=False)
    is_active       = models.BooleanField(default=True)
    is_staff        = models.BooleanField(default=False)
    is_superuser    = models.BooleanField(default=False)

    partner         = models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.SET_NULL,
                        null=True,
                        blank=True,
                        related_name='partners',
                        help_text="Select a partner for 50/50 splits."
    )

    legal_name      = models.CharField(max_length=100, null=True, blank=True) #this should not be null as it is required for filtering out redundant transaction info.

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', ]

    objects = MyAccountManager()

    def __str__(self):
        return self.email
    
    def has_perm(self, perm, obj=None):
        return self.is_admin
    
    def has_module_perms(self, app_label):
        return True


# for allowing the user to sort transactions in to categories which can be used for filtering or reporting.
# label example: "Groceries", "Fuel", "Entertainment", "Bills", "Rent", "Salary", "Other"
class TransactionLabels(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transaction_labels'
    )
    label               = models.CharField(max_length=50, null=False, blank=False)
    transaction_name    = models.CharField(max_length=50, null=False, blank=False)

    class Meta:
        unique_together = [['user', 'label']]

    def __str__(self):
        return f"{self.user} label: {self.label} for {self.transaction_name}"