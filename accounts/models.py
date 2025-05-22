from datetime import date
from tkinter import CENTER
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

from accounts.choices import DeviceType, Gender, Section
from common.models import BaseModel

HEIGHT_UNITS = [
    ("cm", "Centimeters"),
    ("ft", "Feet"),
    ("in", "Inches"),
    ("m", "Meters"),
]

class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)


    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)
    
class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, blank=True, null=True, db_index=True, verbose_name="email address")

    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    gender = models.CharField(choices=Gender, max_length=50)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    # phone number verification
    phone_number_verified = models.BooleanField(default=False)
    phone_number_verified_at = models.DateTimeField(null=True, blank=True)
    phone_number = models.CharField(max_length=14, null=True, blank=True, unique=True)
    account_verified = models.BooleanField(default=False)
    account_verified_at = models.DateTimeField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    date_of_birth = models.DateTimeField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    height_unit = models.CharField(max_length=5, choices=HEIGHT_UNITS, default="cm")

    wellness_status = models.CharField(max_length=100, null=True, blank=True)  # ["Healthy", "Sick", "Injured"]
    referral_source = models.CharField(max_length=100, null=True, blank=True)
    goals = models.JSONField(default=list, blank=True)  # ["Reduce cloud costs", "Generate billing reports", etc.]

    has_completed_onboarding = models.BooleanField(default=False)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    
    allow_push_notifications = models.BooleanField(default=False)
    allow_ovulation_tracker = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    
    country = models.CharField(max_length=100, default="Canada")
    
    device_token = models.TextField(null=True, blank=False)
    device_type = models.CharField(default=DeviceType.Android, choices=DeviceType, max_length=50)
    
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ("-created_at",)
        
    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = date.today()
        dob = self.date_of_birth.date()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower().strip()
        super().save(*args, **kwargs)
        

class PromptHistory(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    section = models.CharField(choices=Section, max_length=50)
    prompt = models.TextField()
    response = models.TextField()

    class Meta:
        ordering = ['-created_at']