import re

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import RoleChoices, User
from academics.models import Instructor, Program, ProgramUniformImage
from alumni.models import Alumni
from content.models import Announcement, Event, News, PublicationStatus
from content.richtext import sanitize_richtext
from departments.models import CalendarImage, Department, SchoolInfo

UPDATE_TYPE_CHOICES = (
    ("announcement", "Announcement"),
    ("news", "News"),
)
CONTENT_VIDEO_HELP_TEXT = "Optional. Upload a video for this post. Portrait and landscape layouts are supported. MP4 works best."
CONTENT_IMAGE_HELP_TEXT = "Optional. Upload a cover image. If you also upload a video, the image will be used as the video poster when available."


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


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    def clean(self, data, initial=None):
        if not data:
            return []

        if not isinstance(data, (list, tuple)):
            data = [data]

        cleaned_files = []
        for uploaded_file in data:
            if not uploaded_file:
                continue
            cleaned_files.append(super().clean(uploaded_file, initial))
        return cleaned_files


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
    calendar_images = MultipleImageField(
        required=False,
        widget=MultipleFileInput(
            attrs={
                "class": "form-control",
                "accept": "image/*",
                "multiple": True,
            }
        ),
    )
    remove_calendar_images = forms.ModelMultipleChoiceField(
        queryset=CalendarImage.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    top_calendar_image = forms.ModelChoiceField(
        queryset=CalendarImage.objects.none(),
        required=False,
        empty_label=None,
    )

    class Meta:
        model = SchoolInfo
        fields = (
            "college_name",
            "landing_background_image",
            "mission",
            "vision",
            "strategic_goals",
            "core_values",
            "quality_policy",
            "history",
            "history_image",
        )
        widgets = {
            "college_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Negros Oriental State University",
                }
            ),
            "landing_background_image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
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
            "strategic_goals": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Enter the university strategic goals.",
                }
            ),
            "core_values": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 8,
                    "placeholder": "Enter one core value per paragraph. Put the title on the first line and an optional description below it.",
                }
            ),
            "quality_policy": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Enter the university quality policy.",
                }
            ),
            "history": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Enter the university history content.",
                }
            ),
            "history_image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        calendar_images_queryset = (
            self.instance.calendar_images.all()
            if self.instance is not None and self.instance.pk
            else CalendarImage.objects.none()
        )
        self.fields["remove_calendar_images"].queryset = calendar_images_queryset
        self.fields["top_calendar_image"].queryset = calendar_images_queryset
        if not self.is_bound and calendar_images_queryset.exists():
            self.fields["top_calendar_image"].initial = calendar_images_queryset.first().pk
        self.fields["landing_background_image"].help_text = (
            "Shown as the homepage opening background. Upload the campus photo you want visitors to see first."
        )
        self.fields["calendar_images"].help_text = (
            "Shown on the public NORSU Calendar page. You can select one or more pictures at the same time. Uploading new pictures replaces the current set."
        )
        self.fields["remove_calendar_images"].help_text = "Select any current calendar pictures you want to remove."
        self.fields["top_calendar_image"].help_text = "Click a current picture to make it appear first on the public NORSU Calendar page."
        self.fields["core_values"].help_text = "Use one paragraph per value. First line becomes the card title, and the next lines become the description."

    @staticmethod
    def delete_calendar_image(calendar_image):
        if calendar_image.image:
            calendar_image.image.delete(save=False)
        calendar_image.delete()

    def save(self, commit=True):
        school_info = super().save(commit=commit)

        if not commit:
            return school_info

        uploaded_images = self.cleaned_data.get("calendar_images", [])

        if uploaded_images:
            for calendar_image in school_info.calendar_images.all():
                self.delete_calendar_image(calendar_image)
            for index, uploaded_image in enumerate(uploaded_images):
                CalendarImage.objects.create(
                    school_info=school_info,
                    image=uploaded_image,
                    sort_order=index,
                )
        else:
            removed_calendar_images = list(self.cleaned_data.get("remove_calendar_images", []))
            for calendar_image in removed_calendar_images:
                self.delete_calendar_image(calendar_image)
            selected_top_image = self.cleaned_data.get("top_calendar_image")
            removed_calendar_image_ids = {calendar_image.pk for calendar_image in removed_calendar_images}
            remaining_calendar_images = list(school_info.calendar_images.all())

            if selected_top_image and selected_top_image.pk not in removed_calendar_image_ids:
                remaining_calendar_images = [
                    selected_top_image,
                    *[calendar_image for calendar_image in remaining_calendar_images if calendar_image.pk != selected_top_image.pk],
                ]

            for index, calendar_image in enumerate(remaining_calendar_images):
                if calendar_image.sort_order != index:
                    calendar_image.sort_order = index
                    calendar_image.save(update_fields=["sort_order"])

        return school_info


class DepartmentScopedAdminFormMixin:
    department_field_name = "department"
    allow_blank_department_for_super_admin = False

    def __init__(self, *args, user=None, save_action="", **kwargs):
        self.save_action = save_action or ""
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
        elif user and user.role == RoleChoices.SUPER_ADMIN and self.allow_blank_department_for_super_admin:
            department_field.widget = forms.HiddenInput()
            department_field.required = False

    def clean_department(self):
        department = self.cleaned_data.get(self.department_field_name)

        if self.user and self.user.role == RoleChoices.DEPARTMENT_ADMIN:
            return self.user.department

        if self.user and self.user.role == RoleChoices.SUPER_ADMIN and self.allow_blank_department_for_super_admin:
            return None

        if department is None:
            raise ValidationError("Please select a department.")

        return department

    def is_saving_draft(self):
        return self.save_action == "draft"

    def has_draft_value(self, field_name):
        value = self.cleaned_data.get(field_name)
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        return True

    def ensure_draft_has_content(self, field_names, *, message):
        if not self.is_saving_draft():
            return
        if any(self.has_draft_value(field_name) for field_name in field_names):
            return
        raise ValidationError(message)


class DepartmentAdminAccountFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assigned_department_ids = User.objects.filter(
            role=RoleChoices.DEPARTMENT_ADMIN,
            department__isnull=False,
        ).values_list("department_id", flat=True)
        self.fields["department"].queryset = Department.objects.exclude(pk__in=assigned_department_ids).order_by("name")

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


class DepartmentThemeColorFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        primary_color = getattr(self.instance, "theme_color", "") or "#12345b"
        secondary_color = getattr(self.instance, "theme_color_secondary", "") or primary_color

        if "theme_color" in self.fields and not self.is_bound:
            self.fields["theme_color"].initial = primary_color

        if "theme_color_secondary" in self.fields and not self.is_bound:
            self.fields["theme_color_secondary"].initial = secondary_color

    def _clean_hex_color(self, field_name, *, label, allow_blank=False):
        value = (self.cleaned_data.get(field_name) or "").strip()
        if not value and allow_blank:
            return ""
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
            raise ValidationError(f"{label} must be a valid hex color like #12345b.")
        return value.lower()

    def clean_theme_color(self):
        return self._clean_hex_color("theme_color", label="Theme color 1")

    def clean_theme_color_secondary(self):
        return self._clean_hex_color("theme_color_secondary", label="Theme color 2", allow_blank=True)


class DepartmentForm(DepartmentThemeColorFormMixin, forms.ModelForm):
    class Meta:
        model = Department
        fields = (
            "name",
            "code",
            "description",
            "mission",
            "vision",
            "dean_name",
            "dean_photo",
            "assistant_dean_name",
            "assistant_dean_photo",
            "logo",
        )
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
            "mission": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter the department mission statement.",
                }
            ),
            "vision": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter the department vision statement.",
                }
            ),
            "dean_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Dr. Maria Santos"}
            ),
            "dean_photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "assistant_dean_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Prof. Allan Reyes"}
            ),
            "assistant_dean_photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9\s-]*", code):
            raise ValidationError("Department code may only contain uppercase letters, numbers, spaces, and hyphens.")
        return code


class DepartmentLeadershipForm(DepartmentThemeColorFormMixin, forms.ModelForm):
    class Meta:
        model = Department
        fields = (
            "mission",
            "vision",
            "dean_name",
            "dean_photo",
            "assistant_dean_name",
            "assistant_dean_photo",
            "banner_image",
        )
        widgets = {
            "mission": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter your department mission statement",
                }
            ),
            "vision": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter your department vision statement",
                }
            ),
            "dean_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter the dean's full name"}
            ),
            "dean_photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "assistant_dean_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter the assistant dean's full name"}
            ),
            "assistant_dean_photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "banner_image": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }


class ProgramForm(DepartmentScopedAdminFormMixin, forms.ModelForm):
    course_uniform_images = MultipleImageField(
        required=False,
        widget=MultipleFileInput(
            attrs={
                "class": "form-control",
                "accept": "image/*",
                "multiple": True,
            }
        ),
    )
    remove_course_uniform_images = forms.ModelMultipleChoiceField(
        queryset=ProgramUniformImage.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Program
        fields = (
            "program_code",
            "program_name",
            "description",
            "course_uniform_description",
            "department",
        )
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
            "course_uniform_description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Add notes about the official course uniform for this program.",
                }
            ),
            "department": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, user=user, **kwargs)
        self.current_course_uniform_images = list(self.instance.uniform_images.all()) if self.instance.pk else []
        self.legacy_course_uniform_image = (
            self.instance.course_uniform_image
            if self.instance.pk and self.instance.course_uniform_image and not self.current_course_uniform_images
            else None
        )
        self.fields["remove_course_uniform_images"].queryset = (
            self.instance.uniform_images.all() if self.instance.pk else ProgramUniformImage.objects.none()
        )

        if not user or user.role != RoleChoices.DEPARTMENT_ADMIN:
            self.fields.pop("course_uniform_description", None)
            self.fields.pop("course_uniform_images", None)
            self.fields.pop("remove_course_uniform_images", None)
            return

        self.fields["course_uniform_description"].help_text = (
            "Shown on the public department page inside this program's detail view."
        )
        self.fields["course_uniform_images"].help_text = (
            "You can select one or more pictures at the same time. New uploads are added to the current gallery."
        )
        self.fields["remove_course_uniform_images"].help_text = "Select any current uniform pictures you want to remove."

    @staticmethod
    def delete_course_uniform_image(uniform_image):
        if uniform_image.image:
            uniform_image.image.delete(save=False)
        uniform_image.delete()

    def clean_program_code(self):
        return self.cleaned_data["program_code"].strip().upper()

    def save(self, commit=True):
        program = super().save(commit=commit)

        if not commit or "course_uniform_images" not in self.fields:
            return program

        # Migrate any older single-image record into the gallery the first time the form saves.
        if program.course_uniform_image and not program.uniform_images.exists():
            ProgramUniformImage.objects.create(
                program=program,
                image=program.course_uniform_image,
                sort_order=0,
            )
            program.course_uniform_image = None
            program.save(update_fields=["course_uniform_image"])

        for uniform_image in self.cleaned_data.get("remove_course_uniform_images", []):
            self.delete_course_uniform_image(uniform_image)

        next_sort_order = program.uniform_images.order_by("-sort_order", "-pk").values_list("sort_order", flat=True).first()
        next_sort_order = 0 if next_sort_order is None else next_sort_order + 1

        for uploaded_image in self.cleaned_data.get("course_uniform_images", []):
            ProgramUniformImage.objects.create(
                program=program,
                image=uploaded_image,
                sort_order=next_sort_order,
            )
            next_sort_order += 1

        return program


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
    allow_blank_department_for_super_admin = True
    draft_title = "Untitled Announcement Draft"

    class Meta:
        model = Announcement
        fields = ("title", "content", "image", "video", "department")
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter announcement title"}
            ),
            "content": TinyMCEWidget(attrs={"placeholder": "Write the announcement content."}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "video": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "video/*"}),
            "department": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, user=user, **kwargs)
        if self.is_saving_draft():
            self.fields["title"].required = False
            self.fields["content"].required = False
        self.fields["image"].help_text = CONTENT_IMAGE_HELP_TEXT
        self.fields["video"].help_text = CONTENT_VIDEO_HELP_TEXT

    def clean_content(self):
        sanitized_content = sanitize_richtext(self.cleaned_data.get("content"))

        if self.is_saving_draft():
            return sanitized_content
        if not sanitized_content.strip():
            raise ValidationError("Please add announcement content before publishing.")

        return sanitized_content

    def clean(self):
        cleaned_data = super().clean()
        self.ensure_draft_has_content(
            ("title", "content", "image", "video"),
            message="Add a title, content, image, or video before saving this announcement as a draft.",
        )
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.is_saving_draft() and not (instance.title or "").strip():
            instance.title = self.draft_title
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class UpdateCreateForm(DepartmentScopedAdminFormMixin, forms.Form):
    allow_blank_department_for_super_admin = True

    content_type = forms.ChoiceField(
        choices=UPDATE_TYPE_CHOICES,
        required=False,
        widget=forms.HiddenInput(),
    )
    title = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter update title"}
        )
    )
    content = forms.CharField(
        widget=TinyMCEWidget(attrs={"placeholder": "Write the update content."})
    )
    image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
    )
    video = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": "video/*"}),
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, user=user, **kwargs)
        initial_type = self.initial.get("content_type") or "news"
        if initial_type not in {"announcement", "news"}:
            initial_type = "news"
        self.fields["content_type"].initial = initial_type
        if self.is_saving_draft():
            self.fields["title"].required = False
            self.fields["content"].required = False
        self.fields["image"].help_text = CONTENT_IMAGE_HELP_TEXT
        self.fields["video"].help_text = CONTENT_VIDEO_HELP_TEXT

    def clean_content(self):
        sanitized_content = sanitize_richtext(self.cleaned_data.get("content"))

        if self.is_saving_draft():
            return sanitized_content
        if not sanitized_content.strip():
            raise ValidationError("Please add update content before publishing.")

        return sanitized_content

    def clean_content_type(self):
        content_type = self.cleaned_data.get("content_type") or self.fields["content_type"].initial or "news"

        if content_type not in {"announcement", "news"}:
            raise ValidationError("Invalid update type.")

        return content_type

    def clean(self):
        cleaned_data = super().clean()
        self.ensure_draft_has_content(
            ("title", "content", "image", "video"),
            message="Add a title, content, image, or video before saving this update as a draft.",
        )
        return cleaned_data

    def save(self, *, posted_by, publication_status=PublicationStatus.PUBLISHED):
        model = Announcement if self.cleaned_data["content_type"] == "announcement" else News
        draft_title = (
            "Untitled Announcement Draft"
            if self.cleaned_data["content_type"] == "announcement"
            else "Untitled News Draft"
        )
        title = (self.cleaned_data.get("title") or "").strip()
        if publication_status == PublicationStatus.DRAFT and not title:
            title = draft_title

        create_kwargs = {
            "title": title,
            "content": self.cleaned_data.get("content", ""),
            "posted_by": posted_by,
            "publication_status": publication_status,
        }

        if self.cleaned_data.get("department") is not None:
            create_kwargs["department"] = self.cleaned_data["department"]
        if self.cleaned_data.get("image"):
            create_kwargs["image"] = self.cleaned_data["image"]
        if self.cleaned_data.get("video"):
            create_kwargs["video"] = self.cleaned_data["video"]

        return model.objects.create(**create_kwargs)

class NewsForm(DepartmentScopedAdminFormMixin, forms.ModelForm):
    allow_blank_department_for_super_admin = True
    draft_title = "Untitled News Draft"

    class Meta:
        model = News
        fields = ("title", "content", "image", "video", "department")
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter news title"}
            ),
            "content": TinyMCEWidget(),
            "image": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "video": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "video/*"}),
            "department": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, user=user, **kwargs)
        if self.is_saving_draft():
            self.fields["title"].required = False
            self.fields["content"].required = False
        self.fields["image"].help_text = CONTENT_IMAGE_HELP_TEXT
        self.fields["video"].help_text = CONTENT_VIDEO_HELP_TEXT

    def clean_content(self):
        sanitized_content = sanitize_richtext(self.cleaned_data.get("content"))

        if self.is_saving_draft():
            return sanitized_content
        if not sanitized_content.strip():
            raise ValidationError("Please add news content before publishing.")

        return sanitized_content

    def clean(self):
        cleaned_data = super().clean()
        self.ensure_draft_has_content(
            ("title", "content", "image", "video"),
            message="Add a title, content, image, or video before saving this news entry as a draft.",
        )
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.is_saving_draft() and not (instance.title or "").strip():
            instance.title = self.draft_title
        if commit:
            instance.save()
            self.save_m2m()
        return instance

class EventForm(DepartmentScopedAdminFormMixin, forms.ModelForm):
    allow_blank_department_for_super_admin = True
    draft_title = "Untitled Event Draft"

    class Meta:
        model = Event
        fields = ("title", "description", "event_date", "end_date", "location", "image", "video", "department")
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter event title"}
            ),
            "description": TinyMCEWidget(attrs={"placeholder": "Write the event description."}),
            "event_date": forms.DateTimeInput(
                attrs={
                    "class": "form-control form-control-datetime",
                    "type": "datetime-local",
                    "step": "900",
                }
            ),
            "end_date": forms.DateTimeInput(
                attrs={
                    "class": "form-control form-control-datetime",
                    "type": "datetime-local",
                    "step": "900",
                }
            ),
            "location": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Event location"}
            ),
            "image": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "video": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "video/*"}),
            "department": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, user=user, **kwargs)

        if self.instance and self.instance.pk and self.instance.event_date:
            self.initial["event_date"] = self.instance.event_date.strftime("%Y-%m-%dT%H:%M")
        if self.instance and self.instance.pk and self.instance.end_date:
            self.initial["end_date"] = self.instance.end_date.strftime("%Y-%m-%dT%H:%M")

        self.fields["end_date"].required = False
        if self.is_saving_draft():
            self.fields["title"].required = False
            self.fields["description"].required = False
            self.fields["event_date"].required = False
            self.fields["location"].required = False
        self.fields["end_date"].help_text = "Optional. Add an end date for multi-day events."
        self.fields["image"].help_text = CONTENT_IMAGE_HELP_TEXT
        self.fields["video"].help_text = CONTENT_VIDEO_HELP_TEXT

    def clean_description(self):
        sanitized_description = sanitize_richtext(self.cleaned_data.get("description"))

        if self.is_saving_draft():
            return sanitized_description
        if not sanitized_description.strip():
            raise ValidationError("Please add event details before publishing.")

        return sanitized_description

    def clean(self):
        cleaned_data = super().clean()
        event_date = cleaned_data.get("event_date")
        end_date = cleaned_data.get("end_date")

        if self.is_saving_draft():
            self.ensure_draft_has_content(
                ("title", "description", "event_date", "end_date", "location", "image", "video"),
                message="Add a title, description, schedule, location, image, or video before saving this event as a draft.",
            )
            if event_date is None:
                cleaned_data["event_date"] = getattr(self.instance, "event_date", None) or end_date or timezone.now()
            return cleaned_data

        if event_date and end_date and end_date < event_date:
            self.add_error("end_date", "End date must be later than the event start date.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.is_saving_draft():
            if not (instance.title or "").strip():
                instance.title = self.draft_title
            instance.event_date = self.cleaned_data.get("event_date") or getattr(instance, "event_date", None) or timezone.now()
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class AlumniForm(DepartmentScopedAdminFormMixin, forms.ModelForm):
    batch_year = forms.TypedChoiceField(
        coerce=int,
        choices=(),
        widget=forms.Select(attrs={"class": "form-select batch-year-select", "size": 1}),
    )
    surname = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    first_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    middle_initial = forms.CharField(
        max_length=1,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    course_program = forms.ChoiceField(
        choices=(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Alumni
        fields = (
            "id_number",
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
            "batch_year": forms.NumberInput(
                attrs={"class": "form-control", "min": 1900}
            ),
            "id_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "inputmode": "numeric",
                    "maxlength": "9",
                    "pattern": r"\d{9}",
                }
            ),
            "department": forms.Select(attrs={"class": "form-select"}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "contact_number": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
            "employment_status": forms.TextInput(attrs={"class": "form-control"}),
            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "job_title": forms.TextInput(attrs={"class": "form-control"}),
            "is_public": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, user=user, **kwargs)
        self.fields["id_number"].required = True

        current_year = timezone.now().year
        self.fields["batch_year"].choices = [
            (year, str(year)) for year in range(current_year, 1999, -1)
        ]

        if self.instance.pk and self.instance.full_name:
            surname, first_name, middle_initial = self._split_full_name(self.instance.full_name)
            self.fields["surname"].initial = surname
            self.fields["first_name"].initial = first_name
            self.fields["middle_initial"].initial = middle_initial

        department = None
        department_field_hidden = isinstance(self.fields["department"].widget, forms.HiddenInput)
        if user and user.role == RoleChoices.DEPARTMENT_ADMIN and user.department_id:
            department = user.department
        else:
            department_value = self.data.get("department") if self.is_bound else self.initial.get("department")
            if not department_value and self.instance.pk:
                department_value = self.instance.department_id

            if isinstance(department_value, Department):
                department = department_value
            elif department_value:
                department = Department.objects.filter(pk=department_value).first()

        program_queryset = Program.objects.select_related("department").order_by("department__name", "program_name")
        empty_choice_label = "Select a program"
        if department is not None:
            program_queryset = program_queryset.filter(department=department)
        elif not department_field_hidden:
            program_queryset = Program.objects.none()
            empty_choice_label = "Select a department first"

        program_choices = [("", empty_choice_label)]
        program_choices.extend((str(program), str(program)) for program in program_queryset)

        current_value = self.data.get("course_program") if self.is_bound else self.initial.get("course_program")
        if not current_value and self.instance.pk:
            current_value = self.instance.course_program

        if current_value and all(value != current_value for value, _ in program_choices):
            program_choices.append((current_value, current_value))

        self.fields["course_program"].choices = program_choices

    @staticmethod
    def _split_full_name(full_name):
        name = (full_name or "").strip()
        if not name:
            return "", "", ""

        if "," in name:
            surname, given_part = [part.strip() for part in name.split(",", 1)]
            given_tokens = given_part.split()
            if len(given_tokens) > 1 and len(given_tokens[-1].rstrip(".")) == 1:
                middle_initial = given_tokens[-1].rstrip(".").upper()
                first_name = " ".join(given_tokens[:-1])
            else:
                middle_initial = ""
                first_name = given_part
            return surname, first_name, middle_initial

        tokens = name.split()
        if len(tokens) == 1:
            return tokens[0], "", ""
        if len(tokens) == 2:
            return tokens[1], tokens[0], ""

        surname = tokens[-1]
        if len(tokens[-2].rstrip(".")) == 1:
            middle_initial = tokens[-2].rstrip(".").upper()
            first_name = " ".join(tokens[:-2])
        else:
            middle_initial = ""
            first_name = " ".join(tokens[:-1])
        return surname, first_name, middle_initial

    def clean_middle_initial(self):
        middle_initial = (self.cleaned_data.get("middle_initial") or "").strip().rstrip(".")
        if len(middle_initial) > 1:
            raise ValidationError("Middle initial must be a single letter.")
        return middle_initial.upper()

    def clean_id_number(self):
        id_number = (self.cleaned_data.get("id_number") or "").strip()
        if not id_number:
            raise ValidationError("Please enter the alumni ID number.")
        if not re.fullmatch(r"\d{9}", id_number):
            raise ValidationError("ID number must be exactly 9 numbers.")
        return id_number

    def clean(self):
        cleaned_data = super().clean()
        surname = (cleaned_data.get("surname") or "").strip()
        first_name = (cleaned_data.get("first_name") or "").strip()
        middle_initial = (cleaned_data.get("middle_initial") or "").strip()

        if surname and first_name:
            cleaned_data["full_name"] = f"{surname}, {first_name}{f' {middle_initial}.' if middle_initial else ''}"

        return cleaned_data

    def save(self, commit=True):
        self.instance.full_name = self.cleaned_data["full_name"]
        return super().save(commit=commit)


class AlumniImportForm(forms.Form):
    excel_file = forms.FileField(
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )
    )

    def clean_excel_file(self):
        excel_file = self.cleaned_data["excel_file"]
        if not excel_file.name.lower().endswith(".xlsx"):
            raise ValidationError("Please upload an Excel .xlsx file.")
        return excel_file


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
    password1 = forms.CharField(
        label="Password",
        required=False,
        strip=False,
        help_text="Leave blank to keep the current password.",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "autocomplete": "new-password",
            }
        ),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        required=False,
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "autocomplete": "new-password",
            }
        ),
    )

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.department_id:
            self.fields["department"].queryset = Department.objects.filter(pk=self.instance.department_id)
            self.fields["department"].empty_label = None
            self.fields["department"].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        department = cleaned_data.get("department")
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if self.instance.role != RoleChoices.DEPARTMENT_ADMIN:
            raise ValidationError("This management page is restricted to department admin accounts.")

        if department is None:
            self.add_error("department", "Department admin accounts must be assigned to a department.")
            return cleaned_data

        try:
            self.validate_department_assignment(department)
        except ValidationError as error:
            self.add_error("department", error)

        if password1 or password2:
            if not password1:
                self.add_error("password1", "Please enter the new password.")
            if not password2:
                self.add_error("password2", "Please confirm the new password.")
            if password1 and password2:
                if password1 != password2:
                    self.add_error("password2", "The two password fields didn't match.")
                else:
                    try:
                        password_validation.validate_password(password1, self.instance)
                    except ValidationError as error:
                        self.add_error("password1", error)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get("password1")

        if new_password:
            user.set_password(new_password)

        user.role = RoleChoices.DEPARTMENT_ADMIN
        user.is_staff = True
        user.is_superuser = False

        if commit:
            user.save()

        return user


class SuperAdminAccountUpdateForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        required=False,
        strip=False,
        help_text="Leave blank to keep the current password.",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "autocomplete": "new-password",
            }
        ),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        required=False,
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = User
        fields = ("username", "full_name", "email")
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "super_admin"}
            ),
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Super Admin"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "admin@norsu.edu.ph"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if self.instance.role != RoleChoices.SUPER_ADMIN:
            raise ValidationError("This management page is restricted to the super admin account.")

        if self.instance.department_id is not None:
            self.instance.department = None

        if password1 or password2:
            if not password1:
                self.add_error("password1", "Please enter the new password.")
            if not password2:
                self.add_error("password2", "Please confirm the new password.")
            if password1 and password2:
                if password1 != password2:
                    self.add_error("password2", "The two password fields didn't match.")
                else:
                    try:
                        password_validation.validate_password(password1, self.instance)
                    except ValidationError as error:
                        self.add_error("password1", error)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get("password1")

        if new_password:
            user.set_password(new_password)

        user.role = RoleChoices.SUPER_ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.department = None
        user.is_active = True

        if commit:
            user.save()

        return user
