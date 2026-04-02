import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import RoleChoices, User
from academics.models import Instructor, Program
from alumni.models import Alumni
from content.models import Announcement, Event, News
from content.richtext import sanitize_richtext
from departments.models import Department, SchoolInfo


class TinyMCEWidget(forms.Textarea):
    class Media:
        js = (
            "vendor/tinymce/tinymce.min.js",
            "js/news_editor.js",
        )

    def __init__(self, attrs=None):
        default_attrs = {
            "class": "form-control",
            "rows": 18,
            "placeholder": "Write the news content.",
            "data-richtext-editor": "tinymce",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "full_name", "email", "role", "department")


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


class AdminAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "Username",
                "autofocus": True,
            }
        )
    )
    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "Password",
            }
        ),
    )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

        if user.role not in {RoleChoices.SUPER_ADMIN, RoleChoices.DEPARTMENT_ADMIN}:
            raise ValidationError(
                "This portal is restricted to admin accounts.",
                code="invalid_login_role",
            )


class SchoolInfoForm(forms.ModelForm):
    class Meta:
        model = SchoolInfo
        fields = ("college_name", "mission", "vision", "history")
        widgets = {
            "college_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Negros Oriental State University",
                }
            ),
            "mission": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter the university mission statement.",
                }
            ),
            "vision": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter the university vision statement.",
                }
            ),
            "history": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Enter the university history content.",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class DepartmentScopedAdminFormMixin:
    department_field_name = "department"

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        department_field = self.fields.get(self.department_field_name)

        if department_field is None:
            return

        department_field.queryset = Department.objects.filter(is_active=True).order_by("name")

        if user and user.role == RoleChoices.DEPARTMENT_ADMIN and user.department_id:
            department_field.queryset = Department.objects.filter(pk=user.department_id)
            department_field.initial = user.department
            department_field.widget = forms.HiddenInput()
            department_field.required = False

    def clean_department(self):
        department = self.cleaned_data.get(self.department_field_name)

        if self.user and self.user.role == RoleChoices.DEPARTMENT_ADMIN:
            return self.user.department

        if department is None:
            raise ValidationError("Please select a department.")

        return department


class DepartmentAdminAccountFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(is_active=True).order_by("name")

    def validate_department_assignment(self, department):
        if department is None:
            raise ValidationError("Department admin accounts must be assigned to a department.")

        existing_admin = User.objects.filter(
            role=RoleChoices.DEPARTMENT_ADMIN,
            department=department,
        )

        if self.instance.pk:
            existing_admin = existing_admin.exclude(pk=self.instance.pk)

        if existing_admin.exists():
            raise ValidationError("This department already has an assigned department admin.")

        return department


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ("name", "code", "description", "logo", "theme_color")
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "College of Arts and Sciences"}
            ),
            "code": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "CAS"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter a short overview for this department.",
                }
            ),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "theme_color": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "#12345b"}
            ),
        }

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9\s-]*", code):
            raise ValidationError("Department code may only contain uppercase letters, numbers, spaces, and hyphens.")
        return code

    def clean_theme_color(self):
        theme_color = self.cleaned_data["theme_color"].strip()
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", theme_color):
            raise ValidationError("Theme color must be a valid hex color like #12345b.")
        return theme_color.lower()


class ProgramForm(DepartmentScopedAdminFormMixin, forms.ModelForm):
    class Meta:
        model = Program
        fields = ("program_code", "program_name", "description", "department")
        widgets = {
            "program_code": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "BSIT"}
            ),
            "program_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Bachelor of Science in Information Technology"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter a short description for this program.",
                }
            ),
            "department": forms.Select(attrs={"class": "form-select"}),
        }

    def clean_program_code(self):
        return self.cleaned_data["program_code"].strip().upper()


class InstructorForm(DepartmentScopedAdminFormMixin, forms.ModelForm):
    class Meta:
        model = Instructor
        fields = ("full_name", "photo", "department")
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Juan Dela Cruz"}
            ),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "department": forms.Select(attrs={"class": "form-select"}),
        }

class AnnouncementForm(DepartmentScopedAdminFormMixin, forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ("title", "content", "image", "department")
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter announcement title"}
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Write the announcement content.",
                }
            ),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "department": forms.Select(attrs={"class": "form-select"}),
        }

class NewsForm(DepartmentScopedAdminFormMixin, forms.ModelForm):
    class Meta:
        model = News
        fields = ("title", "content", "image", "department")
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter news title"}
            ),
            "content": TinyMCEWidget(),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "department": forms.Select(attrs={"class": "form-select"}),
        }

    def clean_content(self):
        sanitized_content = sanitize_richtext(self.cleaned_data.get("content"))

        if not sanitized_content.strip():
            raise ValidationError("Please add news content before publishing.")

        return sanitized_content

class EventForm(DepartmentScopedAdminFormMixin, forms.ModelForm):
    class Meta:
        model = Event
        fields = ("title", "description", "event_date", "location", "image", "department")
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter event title"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Write the event description.",
                }
            ),
            "event_date": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "location": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Event location"}
            ),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "department": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, user=user, **kwargs)

        if self.instance and self.instance.pk and self.instance.event_date:
            self.initial["event_date"] = self.instance.event_date.strftime("%Y-%m-%dT%H:%M")


class AlumniForm(DepartmentScopedAdminFormMixin, forms.ModelForm):
    class Meta:
        model = Alumni
        fields = (
            "full_name",
            "batch_year",
            "course_program",
            "department",
            "photo",
            "email",
            "contact_number",
            "address",
            "employment_status",
            "company_name",
            "job_title",
            "is_public",
        )
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Maria Santos"}
            ),
            "batch_year": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "2024", "min": 1900}
            ),
            "course_program": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "BSIT - Bachelor of Science in Information Technology"}
            ),
            "department": forms.Select(attrs={"class": "form-select"}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "name@example.com"}
            ),
            "contact_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "+63 912 345 6789"}
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Private alumni address",
                }
            ),
            "employment_status": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Employed"}
            ),
            "company_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Company name"}
            ),
            "job_title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Job title"}
            ),
            "is_public": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class DepartmentAdminCreationForm(DepartmentAdminAccountFormMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "full_name", "email", "department", "is_active")
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "cted_admin"}
            ),
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Department Administrator"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "admin@norsu.edu.ph"}
            ),
            "department": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["is_active"].initial = True

    def clean_department(self):
        return self.validate_department_assignment(self.cleaned_data.get("department"))

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = RoleChoices.DEPARTMENT_ADMIN
        user.is_staff = True
        user.is_superuser = False

        if commit:
            user.save()

        return user


class DepartmentAdminUpdateForm(DepartmentAdminAccountFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "full_name", "email", "department", "is_active")
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "cted_admin"}
            ),
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Department Administrator"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "admin@norsu.edu.ph"}
            ),
            "department": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        department = cleaned_data.get("department")

        if self.instance.role != RoleChoices.DEPARTMENT_ADMIN:
            raise ValidationError("This management page is restricted to department admin accounts.")

        if department is None:
            self.add_error("department", "Department admin accounts must be assigned to a department.")
            return cleaned_data

        try:
            self.validate_department_assignment(department)
        except ValidationError as error:
            self.add_error("department", error)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = RoleChoices.DEPARTMENT_ADMIN
        user.is_staff = True
        user.is_superuser = False

        if commit:
            user.save()

        return user
