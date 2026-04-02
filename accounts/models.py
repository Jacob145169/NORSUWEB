from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class RoleChoices(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super Admin"
    DEPARTMENT_ADMIN = "department_admin", "Department Admin"


class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", RoleChoices.SUPER_ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("department", None)

        if extra_fields["role"] != RoleChoices.SUPER_ADMIN:
            raise ValueError("Superuser must have the 'super_admin' role.")

        return super().create_superuser(username, email=email, password=password, **extra_fields)


class User(AbstractUser):
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=32, choices=RoleChoices.choices)
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )

    objects = CustomUserManager()
    REQUIRED_FIELDS = ["email", "full_name", "role"]

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(role=RoleChoices.SUPER_ADMIN) & Q(department__isnull=True))
                    | (Q(role=RoleChoices.DEPARTMENT_ADMIN) & Q(department__isnull=False))
                ),
                name="accounts_user_role_department_valid",
            ),
            models.UniqueConstraint(
                fields=["role"],
                condition=Q(role=RoleChoices.SUPER_ADMIN),
                name="accounts_single_super_admin",
            ),
            models.UniqueConstraint(
                fields=["department"],
                condition=Q(role=RoleChoices.DEPARTMENT_ADMIN),
                name="accounts_unique_department_admin",
            ),
        ]

    def clean(self):
        super().clean()

        if self.role == RoleChoices.SUPER_ADMIN and self.department_id is not None:
            raise ValidationError({"department": "Super admin must not be assigned to a department."})

        if self.role == RoleChoices.DEPARTMENT_ADMIN and self.department_id is None:
            raise ValidationError({"department": "Department admin must be assigned to a department."})

    def save(self, *args, **kwargs):
        if self.role == RoleChoices.SUPER_ADMIN:
            self.department = None
            self.is_staff = True
        elif self.role == RoleChoices.DEPARTMENT_ADMIN:
            self.is_staff = True

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.full_name or self.username
