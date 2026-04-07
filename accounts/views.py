from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import CharField, Q
from django.db.models.functions import Cast
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, FormView, ListView, RedirectView, TemplateView, UpdateView

from .forms import (
    AdminAuthenticationForm,
    AlumniForm,
    AlumniImportForm,
    AnnouncementForm,
    DepartmentAdminCreationForm,
    DepartmentAdminUpdateForm,
    DepartmentForm,
    DepartmentLeadershipForm,
    EventForm,
    InstructorForm,
    NewsForm,
    ProgramForm,
    SchoolInfoForm,
    UpdateCreateForm,
)
from .models import RoleChoices, User
from .pdf import build_alumni_pdf, build_alumni_record_lines
from .permissions import (
    DepartmentAdminRequiredMixin,
    DepartmentScopedQuerysetMixin,
    PortalLoginRequiredMixin,
    SuperAdminRequiredMixin,
)
from .view_mixins import PageMetadataMixin, SuccessMessageMixin, UserFormKwargsMixin
from .xlsx import WorkbookReadError, load_first_sheet_rows
from academics.models import Instructor, Program
from alumni.models import Alumni
from content.models import Announcement, Event, News, PublicationStatus
from departments.models import Department, SchoolInfo


def build_updates_collection(announcements, news_items):
    updates = []

    for announcement in announcements:
        announcement.update_kind = "Announcement"
        announcement.is_news = False
        updates.append(announcement)

    for item in news_items:
        item.update_kind = "News"
        item.is_news = True
        updates.append(item)

    updates.sort(key=lambda item: item.date_posted, reverse=True)
    return updates


def get_scoped_update_querysets(user):
    announcements = Announcement.objects.select_related("department", "posted_by").order_by("-date_posted")
    news_items = News.objects.select_related("department", "posted_by").order_by("-date_posted")

    if user.role == RoleChoices.DEPARTMENT_ADMIN and user.department_id:
        announcements = announcements.filter(department=user.department)
        news_items = news_items.filter(department=user.department)

    return announcements, news_items


class AdminLoginView(LoginView):
    authentication_form = AdminAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        if self.request.user.role == RoleChoices.SUPER_ADMIN:
            return reverse("accounts:super_admin_dashboard")
        if self.request.user.role == RoleChoices.DEPARTMENT_ADMIN:
            return reverse("accounts:department_admin_dashboard")
        return reverse("accounts:login")


def admin_logout(request):
    logout(request)
    return redirect("accounts:login")


class DashboardRedirectView(PortalLoginRequiredMixin, RedirectView):
    pattern_name = "accounts:login"

    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.role == RoleChoices.SUPER_ADMIN:
            return reverse("accounts:super_admin_dashboard")
        if self.request.user.role == RoleChoices.DEPARTMENT_ADMIN:
            return reverse("accounts:department_admin_dashboard")
        return reverse("accounts:login")


class ProgramAccessMixin(DepartmentScopedQuerysetMixin):
    model = Program

    def get_program_queryset(self):
        queryset = Program.objects.select_related("department").order_by("department__name", "program_name")
        return self.scope_to_user_department(queryset)


class ProgramFormMixin(UserFormKwargsMixin, ProgramAccessMixin):
    form_class = ProgramForm

    def get_success_url(self):
        return reverse("accounts:program_list")


class InstructorAccessMixin(DepartmentScopedQuerysetMixin):
    model = Instructor

    def get_instructor_queryset(self):
        queryset = Instructor.objects.select_related("department").order_by("department__name", "full_name")
        return self.scope_to_user_department(queryset)


class InstructorFormMixin(UserFormKwargsMixin, InstructorAccessMixin):
    form_class = InstructorForm

    def get_success_url(self):
        return reverse("accounts:instructor_list")


class DraftWorkflowMixin:
    draft_edit_url_name = ""
    published_list_url_name = ""
    draft_saved_message = "Draft saved successfully."
    published_from_draft_message = "Draft published successfully."
    published_create_message = "Content created successfully."
    published_update_message = "Content updated successfully."

    def get_save_action(self):
        return "draft" if self.request.POST.get("save_action") == "draft" else "publish"

    def is_saving_draft(self):
        return self.get_save_action() == "draft"

    def get_draft_success_url(self):
        return reverse(self.draft_edit_url_name, kwargs={"pk": self.object.pk})

    def get_success_url(self):
        if self.is_saving_draft():
            return self.get_draft_success_url()
        return reverse(self.published_list_url_name)

    def get_submit_labels(self):
        object_instance = getattr(self, "object", None)
        if object_instance is not None and getattr(object_instance, "is_draft", False):
            return {
                "submit_label": "Publish",
                "draft_label": "Save Draft",
            }
        return {
            "submit_label": getattr(self, "submit_label", "Save Changes"),
            "draft_label": "Save Draft",
        }


class DraftableModelFormMixin(DraftWorkflowMixin):
    def form_valid(self, form):
        was_update = form.instance.pk is not None
        previous_status = None

        if was_update:
            previous_status = type(form.instance).objects.filter(pk=form.instance.pk).values_list(
                "publication_status",
                flat=True,
            ).first()

        form.instance.posted_by = self.request.user
        form.instance.publication_status = (
            PublicationStatus.DRAFT if self.is_saving_draft() else PublicationStatus.PUBLISHED
        )

        if previous_status == PublicationStatus.DRAFT and not self.is_saving_draft():
            form.instance.date_posted = timezone.now()

        response = super().form_valid(form)
        messages.success(
            self.request,
            self.get_form_success_message(
                was_update=was_update,
                previous_status=previous_status,
            ),
        )
        return response

    def get_form_success_message(self, *, was_update, previous_status):
        if self.is_saving_draft():
            return self.draft_saved_message
        if previous_status == PublicationStatus.DRAFT:
            return self.published_from_draft_message
        return self.published_update_message if was_update else self.published_create_message


class AnnouncementAccessMixin(DepartmentScopedQuerysetMixin):
    model = Announcement

    def get_announcement_queryset(self):
        queryset = Announcement.objects.select_related("department", "posted_by").order_by("-date_posted")
        return self.scope_to_user_department(queryset)


class AnnouncementFormMixin(UserFormKwargsMixin, DraftableModelFormMixin, AnnouncementAccessMixin):
    form_class = AnnouncementForm
    draft_edit_url_name = "accounts:announcement_update"
    published_list_url_name = "accounts:update_list"
    draft_saved_message = "Announcement draft saved successfully."
    published_from_draft_message = "Announcement draft published successfully."
    published_create_message = "Announcement created successfully."
    published_update_message = "Announcement updated successfully."


class NewsAccessMixin(DepartmentScopedQuerysetMixin):
    model = News

    def get_news_queryset(self):
        queryset = News.objects.select_related("department", "posted_by").order_by("-date_posted")
        return self.scope_to_user_department(queryset)


class NewsFormMixin(UserFormKwargsMixin, DraftableModelFormMixin, NewsAccessMixin):
    form_class = NewsForm
    draft_edit_url_name = "accounts:news_update"
    published_list_url_name = "accounts:update_list"
    draft_saved_message = "News draft saved successfully."
    published_from_draft_message = "News draft published successfully."
    published_create_message = "News entry created successfully."
    published_update_message = "News entry updated successfully."


class EventAccessMixin(DepartmentScopedQuerysetMixin):
    model = Event

    def get_event_queryset(self):
        queryset = Event.objects.select_related("department", "posted_by").order_by("event_date", "-date_posted")
        return self.scope_to_user_department(queryset)


class EventFormMixin(UserFormKwargsMixin, DraftableModelFormMixin, EventAccessMixin):
    form_class = EventForm
    draft_edit_url_name = "accounts:event_update"
    published_list_url_name = "accounts:event_list"
    draft_saved_message = "Event draft saved successfully."
    published_from_draft_message = "Event draft published successfully."
    published_create_message = "Event created successfully."
    published_update_message = "Event updated successfully."


class AlumniAccessMixin(DepartmentScopedQuerysetMixin):
    model = Alumni
    allowed_roles = (RoleChoices.DEPARTMENT_ADMIN,)

    def get_alumni_queryset(self):
        queryset = Alumni.objects.select_related("department").order_by("-batch_year", "full_name")
        return self.scope_to_user_department(queryset)


class AlumniFormMixin(UserFormKwargsMixin, AlumniAccessMixin):
    form_class = AlumniForm

    def get_success_url(self):
        return reverse("accounts:alumni_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        program_options_by_department = {}

        for program in Program.objects.select_related("department").order_by("department__name", "program_name"):
            department_id = str(program.department_id)
            program_options_by_department.setdefault(department_id, []).append(
                {"value": str(program), "label": str(program)}
            )

        context["program_options_by_department"] = program_options_by_department
        return context


class SuperAdminDashboardView(SuperAdminRequiredMixin, TemplateView):
    template_name = "accounts/super_admin_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Super Admin Dashboard"
        context["overview_stats"] = [
            {"label": "Total Departments", "value": Department.objects.count()},
            {"label": "Total Programs", "value": Program.objects.count()},
            {"label": "Total Instructors", "value": Instructor.objects.count()},
            {"label": "Total Updates", "value": Announcement.objects.count() + News.objects.count()},
            {"label": "Total Events", "value": Event.objects.count()},
            {"label": "Total Alumni", "value": Alumni.objects.count()},
        ]
        context["management_sections"] = [
            {
                "title": "Landing Page and School Content",
                "description": "Maintain the public homepage content and institution-wide information.",
                "items": [
                    "Edit landing page content",
                    "Manage mission, vision, and history",
                    "Update school-wide messaging",
                ],
            },
            {
                "title": "Department and Admin Management",
                "description": "Control academic units and administrator access across the system.",
                "items": [
                    "Add, edit, and delete departments",
                    "Manage department admin accounts",
                    "Review department structure and assignments",
                ],
            },
            {
                "title": "Academic and Public Content",
                "description": "Oversee all records that appear across departments and public pages.",
                "items": [
                    "Manage all programs and instructors",
                    "Manage all updates and events",
                ],
            },
        ]
        context["quick_links"] = [
            {"title": "Mission and Vision", "detail": "Edit homepage mission, vision, and history content", "url": reverse("accounts:school_info_update")},
            {"title": "Departments", "detail": "Create and organize department records", "url": reverse("accounts:department_list")},
            {"title": "Department Admin Accounts", "detail": "Manage department-level administrator access", "url": reverse("accounts:department_admin_list")},
            {"title": "Programs", "detail": "Oversee all academic programs", "url": reverse("accounts:program_list")},
            {"title": "Instructors", "detail": "Maintain instructor profiles", "url": reverse("accounts:instructor_list")},
            {"title": "Updates", "detail": "Manage announcements and news from one place", "url": reverse("accounts:update_list")},
            {"title": "Events", "detail": "Manage public events", "url": reverse("accounts:event_list")},
        ]
        context["system_highlights"] = {
            "landing_page_ready": SchoolInfo.objects.exists(),
            "department_admin_count": User.objects.filter(role=RoleChoices.DEPARTMENT_ADMIN).count(),
            "active_departments": Department.objects.filter(is_active=True).count(),
        }
        context["school_info"] = SchoolInfo.objects.first()
        return context


class SchoolInfoUpdateView(PageMetadataMixin, SuccessMessageMixin, SuperAdminRequiredMixin, UpdateView):
    template_name = "accounts/school_info_form.html"
    form_class = SchoolInfoForm
    success_url = reverse_lazy("accounts:super_admin_dashboard")
    dashboard_title = "Edit Homepage Content"
    page_title = "Edit Homepage Mission, Vision, Strategic Goals, Core Values, Quality Policy, History, and Image"
    page_description = "Update the college name, mission, vision, strategic goals, core values, quality policy, history, and the history page image used on the public site."
    success_message = "Landing page content and history media have been updated successfully."

    def get_object(self, queryset=None):
        return SchoolInfo.get_solo()

class DepartmentManagementMixin(SuperAdminRequiredMixin):
    model = Department
    success_url = reverse_lazy("accounts:department_list")


class DepartmentAdminManagementMixin(SuperAdminRequiredMixin):
    model = User
    success_url = reverse_lazy("accounts:department_admin_list")

    def get_department_admin_queryset(self):
        return User.objects.select_related("department").filter(
            role=RoleChoices.DEPARTMENT_ADMIN
        ).order_by("department__name", "full_name", "username")


class DepartmentListView(PageMetadataMixin, DepartmentManagementMixin, ListView):
    template_name = "accounts/department_list.html"
    context_object_name = "departments"
    queryset = Department.objects.order_by("name")
    dashboard_title = "Department Management"
    page_title = "Department Management"
    page_description = "Create, update, and maintain department records used across the public site and admin dashboards."


class DepartmentCreateView(PageMetadataMixin, SuccessMessageMixin, DepartmentManagementMixin, CreateView):
    template_name = "accounts/department_form.html"
    form_class = DepartmentForm
    dashboard_title = "Add Department"
    page_title = "Add Department"
    page_description = "Create a new department with its branding and public overview."
    submit_label = "Create Department"
    success_message = "Department created successfully."


class DepartmentUpdateView(PageMetadataMixin, SuccessMessageMixin, DepartmentManagementMixin, UpdateView):
    template_name = "accounts/department_form.html"
    form_class = DepartmentForm
    dashboard_title = "Edit Department"
    page_description = "Update the department's details, branding, and public overview."
    submit_label = "Save Changes"
    success_message = "Department updated successfully."

    def get_page_title(self):
        return f"Edit {self.object.name}"


class DepartmentLeadershipUpdateView(PageMetadataMixin, SuccessMessageMixin, DepartmentAdminRequiredMixin, UpdateView):
    template_name = "accounts/department_profile_form.html"
    form_class = DepartmentLeadershipForm
    model = Department
    dashboard_title = "Edit Department Profile"
    page_title = "Edit Department Profile"
    page_description = "Update your department mission, vision, leadership details, and banner for the public page."
    submit_label = "Save Profile"
    success_message = "Department profile updated successfully."
    success_url = reverse_lazy("accounts:department_admin_dashboard")

    def get_object(self, queryset=None):
        return self.request.user.department


class DepartmentDeleteView(PageMetadataMixin, SuccessMessageMixin, DepartmentManagementMixin, DeleteView):
    template_name = "accounts/department_confirm_delete.html"
    dashboard_title = "Delete Department"
    page_description = "This action removes the department record from the system."
    success_message = "Department deleted successfully."

    def get_page_title(self):
        return f"Delete {self.object.name}"


class DepartmentAdminListView(PageMetadataMixin, DepartmentAdminManagementMixin, ListView):
    template_name = "accounts/department_admin_list.html"
    context_object_name = "department_admins"
    dashboard_title = "Department Admin Accounts"
    page_title = "Department Admin Accounts"
    page_description = "Create, update, activate, and deactivate department admin accounts linked to each department."

    def get_queryset(self):
        return self.get_department_admin_queryset()


class DepartmentAdminCreateView(PageMetadataMixin, SuccessMessageMixin, DepartmentAdminManagementMixin, CreateView):
    template_name = "accounts/department_admin_form.html"
    form_class = DepartmentAdminCreationForm
    dashboard_title = "Add Department Admin"
    page_title = "Add Department Admin Account"
    page_description = "Create a department admin account and assign it to exactly one department."
    submit_label = "Create Account"
    success_message = "Department admin account created successfully."


class DepartmentAdminUpdateView(PageMetadataMixin, SuccessMessageMixin, DepartmentAdminManagementMixin, UpdateView):
    template_name = "accounts/department_admin_form.html"
    form_class = DepartmentAdminUpdateForm
    dashboard_title = "Edit Department Admin"
    page_description = "Update the account profile, department assignment, and activation status."
    submit_label = "Save Changes"
    success_message = "Department admin account updated successfully."

    def get_queryset(self):
        return self.get_department_admin_queryset()

    def get_page_title(self):
        return f"Edit {self.object.full_name or self.object.username}"


class DepartmentAdminToggleStatusView(DepartmentAdminManagementMixin, View):
    def post(self, request, *args, **kwargs):
        department_admin = get_object_or_404(self.get_department_admin_queryset(), pk=kwargs["pk"])
        department_admin.is_active = not department_admin.is_active
        department_admin.save(update_fields=["is_active"])

        if department_admin.is_active:
            messages.success(request, f"{department_admin.full_name or department_admin.username} has been activated.")
        else:
            messages.success(request, f"{department_admin.full_name or department_admin.username} has been deactivated.")

        return redirect("accounts:department_admin_list")


class ProgramListView(ProgramAccessMixin, ListView):
    template_name = "accounts/program_list.html"
    context_object_name = "programs"

    def get_queryset(self):
        return self.get_program_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.role == RoleChoices.SUPER_ADMIN:
            context["dashboard_title"] = "Program Management"
            context["page_title"] = "Program Management"
            context["page_description"] = "Manage academic programs across all departments."
        else:
            context["dashboard_title"] = f"{user.department.name} Programs"
            context["page_title"] = "Department Program Management"
            context["page_description"] = f"Manage programs for {user.department.name} only."

        return context


class ProgramCreateView(ProgramFormMixin, CreateView):
    template_name = "accounts/program_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Program created successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Add Program"
        context["page_title"] = "Add Program"
        context["page_description"] = "Create a program record with abbreviation, full name, and department assignment."
        context["submit_label"] = "Create Program"
        return context


class ProgramUpdateView(ProgramFormMixin, UpdateView):
    template_name = "accounts/program_form.html"

    def get_queryset(self):
        return self.get_program_queryset()

    def form_valid(self, form):
        messages.success(self.request, "Program updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Edit Program"
        context["page_title"] = f"Edit {self.object.program_code}"
        context["page_description"] = "Update the program abbreviation, full name, description, and department assignment."
        context["submit_label"] = "Save Changes"
        return context


class ProgramDeleteView(ProgramAccessMixin, DeleteView):
    template_name = "accounts/program_confirm_delete.html"
    success_url = reverse_lazy("accounts:program_list")

    def get_queryset(self):
        return self.get_program_queryset()

    def form_valid(self, form):
        messages.success(self.request, "Program deleted successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Delete Program"
        context["page_title"] = f"Delete {self.object.program_code}"
        context["page_description"] = "This action removes the selected program record."
        return context


class InstructorListView(InstructorAccessMixin, ListView):
    template_name = "accounts/instructor_list.html"
    context_object_name = "instructors"

    def get_queryset(self):
        return self.get_instructor_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.role == RoleChoices.SUPER_ADMIN:
            context["dashboard_title"] = "Instructor Management"
            context["page_title"] = "Instructor Management"
            context["page_description"] = "Manage instructor profiles across all departments."
        else:
            context["dashboard_title"] = f"{user.department.name} Instructors"
            context["page_title"] = "Department Instructor Management"
            context["page_description"] = f"Manage instructors for {user.department.name} only."

        return context


class InstructorCreateView(InstructorFormMixin, CreateView):
    template_name = "accounts/instructor_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Instructor created successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Add Instructor"
        context["page_title"] = "Add Instructor"
        context["page_description"] = "Create an instructor profile with name, photo, and department assignment."
        context["submit_label"] = "Create Instructor"
        return context


class InstructorUpdateView(InstructorFormMixin, UpdateView):
    template_name = "accounts/instructor_form.html"

    def get_queryset(self):
        return self.get_instructor_queryset()

    def form_valid(self, form):
        messages.success(self.request, "Instructor updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Edit Instructor"
        context["page_title"] = f"Edit {self.object.full_name}"
        context["page_description"] = "Update the instructor profile, photo, and department assignment."
        context["submit_label"] = "Save Changes"
        return context


class InstructorDeleteView(InstructorAccessMixin, DeleteView):
    template_name = "accounts/instructor_confirm_delete.html"
    success_url = reverse_lazy("accounts:instructor_list")

    def get_queryset(self):
        return self.get_instructor_queryset()

    def form_valid(self, form):
        messages.success(self.request, "Instructor deleted successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Delete Instructor"
        context["page_title"] = f"Delete {self.object.full_name}"
        context["page_description"] = "This action removes the selected instructor profile."
        return context


class UpdatesListView(PortalLoginRequiredMixin, TemplateView):
    template_name = "accounts/update_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        announcements, news_items = get_scoped_update_querysets(user)
        context["updates"] = build_updates_collection(list(announcements), list(news_items))

        if user.role == RoleChoices.SUPER_ADMIN:
            context["dashboard_title"] = "Update Management"
            context["page_title"] = "Update Management"
            context["page_description"] = "Manage announcements and news across all departments."
        else:
            context["dashboard_title"] = f"{user.department.name} Updates"
            context["page_title"] = "Department Update Management"
            context["page_description"] = f"Manage announcements and news for {user.department.name} only."

        return context


class AnnouncementListView(PortalLoginRequiredMixin, RedirectView):
    pattern_name = "accounts:update_list"


class UpdateCreateView(DraftWorkflowMixin, UserFormKwargsMixin, PortalLoginRequiredMixin, FormView):
    template_name = "accounts/update_create_form.html"
    form_class = UpdateCreateForm
    success_url = reverse_lazy("accounts:update_list")
    published_list_url_name = "accounts:update_list"
    draft_saved_message = "Update draft saved successfully."
    published_from_draft_message = "Update draft published successfully."
    published_create_message = "Update created successfully."
    published_update_message = "Update updated successfully."

    def get_initial(self):
        initial = super().get_initial()
        requested_type = self.request.GET.get("type")

        if requested_type in {"announcement", "news"}:
            initial["content_type"] = requested_type

        return initial

    def form_valid(self, form):
        publication_status = (
            PublicationStatus.DRAFT if self.is_saving_draft() else PublicationStatus.PUBLISHED
        )
        update = form.save(
            posted_by=self.request.user,
            publication_status=publication_status,
        )
        self.object = update
        self.draft_edit_url_name = (
            "accounts:announcement_update" if isinstance(update, Announcement) else "accounts:news_update"
        )

        if self.is_saving_draft():
            messages.success(self.request, "Update draft saved successfully.")
        elif isinstance(update, Announcement):
            messages.success(self.request, "Announcement created successfully.")
        else:
            messages.success(self.request, "News entry created successfully.")

        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Add Update"
        context["page_title"] = "Add Update"
        if self.request.user.role == RoleChoices.SUPER_ADMIN:
            context["page_description"] = "Create an update for the homepage and updates page."
        else:
            context["page_description"] = "Create an update for your department."
        context["submit_label"] = "Publish Update"
        context["draft_label"] = "Save Draft"
        return context


class AnnouncementCreateView(PortalLoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return f"{reverse('accounts:update_create')}?type=announcement"


class AnnouncementUpdateView(AnnouncementFormMixin, UpdateView):
    template_name = "accounts/announcement_form.html"

    def get_queryset(self):
        return self.get_announcement_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Edit Announcement"
        context["page_title"] = f"Edit {self.object.title}"
        if self.request.user.role == RoleChoices.SUPER_ADMIN:
            context["page_description"] = "Update the university-wide announcement content and image."
        else:
            context["page_description"] = "Update the announcement content, image, and department assignment."
        context.update(self.get_submit_labels())
        return context


class AnnouncementDeleteView(AnnouncementAccessMixin, DeleteView):
    template_name = "accounts/announcement_confirm_delete.html"
    success_url = reverse_lazy("accounts:update_list")

    def get_queryset(self):
        return self.get_announcement_queryset()

    def form_valid(self, form):
        messages.success(self.request, "Announcement deleted successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Delete Announcement"
        context["page_title"] = f"Delete {self.object.title}"
        context["page_description"] = "This action removes the selected announcement."
        return context


class NewsListView(PortalLoginRequiredMixin, RedirectView):
    pattern_name = "accounts:update_list"


class NewsCreateView(PortalLoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return f"{reverse('accounts:update_create')}?type=news"


class NewsUpdateView(NewsFormMixin, UpdateView):
    template_name = "accounts/news_form.html"

    def get_queryset(self):
        return self.get_news_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Edit News"
        context["page_title"] = f"Edit {self.object.title}"
        if self.request.user.role == RoleChoices.SUPER_ADMIN:
            context["page_description"] = "Update the university-wide news content and image."
        else:
            context["page_description"] = "Update the news content, image, and department assignment."
        context.update(self.get_submit_labels())
        return context


class NewsDeleteView(NewsAccessMixin, DeleteView):
    template_name = "accounts/news_confirm_delete.html"
    success_url = reverse_lazy("accounts:update_list")

    def get_queryset(self):
        return self.get_news_queryset()

    def form_valid(self, form):
        messages.success(self.request, "News entry deleted successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Delete News"
        context["page_title"] = f"Delete {self.object.title}"
        context["page_description"] = "This action removes the selected news entry."
        return context


class EventListView(EventAccessMixin, ListView):
    template_name = "accounts/event_list.html"
    context_object_name = "events"

    def get_queryset(self):
        return self.get_event_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.role == RoleChoices.SUPER_ADMIN:
            context["dashboard_title"] = "Event Management"
            context["page_title"] = "Event Management"
            context["page_description"] = "Manage events across all departments."
        else:
            context["dashboard_title"] = f"{user.department.name} Events"
            context["page_title"] = "Department Event Management"
            context["page_description"] = f"Manage events for {user.department.name} only."

        return context


class EventCreateView(EventFormMixin, CreateView):
    template_name = "accounts/event_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Add Event"
        context["page_title"] = "Add Event"
        if self.request.user.role == RoleChoices.SUPER_ADMIN:
            context["page_description"] = "Create a university-wide event for the public updates page."
        else:
            context["page_description"] = "Create an event entry for the public site."
        context["submit_label"] = "Publish Event"
        context["draft_label"] = "Save Draft"
        return context


class EventUpdateView(EventFormMixin, UpdateView):
    template_name = "accounts/event_form.html"

    def get_queryset(self):
        return self.get_event_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Edit Event"
        context["page_title"] = f"Edit {self.object.title}"
        if self.request.user.role == RoleChoices.SUPER_ADMIN:
            context["page_description"] = "Update the university-wide event details, schedule, and image."
        else:
            context["page_description"] = "Update the event details, schedule, image, and department assignment."
        context.update(self.get_submit_labels())
        return context


class EventDeleteView(EventAccessMixin, DeleteView):
    template_name = "accounts/event_confirm_delete.html"
    success_url = reverse_lazy("accounts:event_list")

    def get_queryset(self):
        return self.get_event_queryset()

    def form_valid(self, form):
        messages.success(self.request, "Event deleted successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Delete Event"
        context["page_title"] = f"Delete {self.object.title}"
        context["page_description"] = "This action removes the selected event."
        return context


class AlumniListView(AlumniAccessMixin, ListView):
    template_name = "accounts/alumni_list.html"
    context_object_name = "alumni_items"

    def get_filtered_queryset(self):
        queryset = self.get_alumni_queryset()
        search_query = (self.request.GET.get("q") or "").strip()
        batch_filter = (self.request.GET.get("batch") or "").strip()
        course_filter = (self.request.GET.get("course") or "").strip()

        if search_query:
            queryset = queryset.annotate(
                batch_year_text=Cast("batch_year", output_field=CharField())
            ).filter(
                Q(full_name__icontains=search_query)
                | Q(id_number__icontains=search_query)
                | Q(course_program__icontains=search_query)
                | Q(batch_year_text__icontains=search_query)
            )

        if batch_filter:
            queryset = queryset.filter(batch_year=batch_filter)

        if course_filter:
            queryset = queryset.filter(
                Q(course_program__iexact=course_filter)
                | Q(course_program__icontains=course_filter)
            )

        return queryset

    def get_queryset(self):
        return self.get_filtered_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        search_query = (self.request.GET.get("q") or "").strip()
        batch_filter = (self.request.GET.get("batch") or "").strip()
        course_filter = (self.request.GET.get("course") or "").strip()

        context["dashboard_title"] = f"{user.department.name} Alumni"
        context["page_title"] = "Department Alumni Management"
        context["page_description"] = f"Manage alumni records for {user.department.name} only."

        context["search_query"] = search_query
        context["selected_batch"] = batch_filter
        context["selected_course"] = course_filter
        current_year = timezone.now().year
        context["batch_options"] = list(range(current_year, 1999, -1))
        program_queryset = Program.objects.select_related("department").order_by("department__name", "program_name")
        if user.role == RoleChoices.DEPARTMENT_ADMIN and user.department_id:
            program_queryset = program_queryset.filter(department=user.department)
        context["course_options"] = [
            {"value": program.program_code, "label": str(program)}
            for program in program_queryset
        ]
        context["has_active_filters"] = bool(search_query or batch_filter or course_filter)
        query_string = self.request.GET.urlencode()
        context["export_pdf_url"] = (
            f"{reverse('accounts:alumni_export_pdf')}?{query_string}"
            if query_string
            else reverse("accounts:alumni_export_pdf")
        )
        return context


class AlumniExportPdfView(AlumniListView, View):
    def get(self, request, *args, **kwargs):
        queryset = list(self.get_filtered_queryset().order_by("course_program", "full_name"))
        user = request.user
        search_query = (request.GET.get("q") or "").strip()
        batch_filter = (request.GET.get("batch") or "").strip()
        course_filter = (request.GET.get("course") or "").strip()

        subtitle_lines = [
            f"Department: {user.department.name}",
            f"Records included: {len(queryset)}",
        ]

        subtitle_lines[0] = f"Department: {user.department.code} DEPARTMENT"

        pdf_bytes = build_alumni_pdf(
            title="Alumni Report",
            subtitle_lines=subtitle_lines,
            record_lines=build_alumni_record_lines(queryset),
            footer_text=f"Generated on {timezone.localtime().strftime('%b %d, %Y %I:%M %p')}",
            logo_file=user.department.logo,
        )

        filename = f"{user.department.code.lower()}-alumni-report.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class AlumniCreateView(AlumniFormMixin, CreateView):
    template_name = "accounts/alumni_form.html"
    import_form_class = AlumniImportForm

    IMPORT_COLUMN_HELP = [
        "last_name",
        "first_name",
        "middle_initial",
        "id_number",
        "batch_year",
        "course_program",
        "email",
        "contact_number",
        "address",
        "employment_status",
        "company_name",
        "job_title",
        "is_public",
    ]

    IMPORT_HEADER_ALIASES = {
        "surname": "surname",
        "last_name": "surname",
        "last name": "surname",
        "first_name": "first_name",
        "first name": "first_name",
        "middle_initial": "middle_initial",
        "middle initial": "middle_initial",
        "mi": "middle_initial",
        "id_number": "id_number",
        "id number": "id_number",
        "batch_year": "batch_year",
        "batch year": "batch_year",
        "course_program": "course_program",
        "course program": "course_program",
        "email": "email",
        "contact_number": "contact_number",
        "contact number": "contact_number",
        "phone": "contact_number",
        "phone number": "contact_number",
        "address": "address",
        "employment_status": "employment_status",
        "employment status": "employment_status",
        "company_name": "company_name",
        "company name": "company_name",
        "job_title": "job_title",
        "job title": "job_title",
        "is_public": "is_public",
        "is public": "is_public",
        "public": "is_public",
    }

    REQUIRED_IMPORT_COLUMNS = {
        "surname",
        "first_name",
        "id_number",
        "batch_year",
        "course_program",
        "email",
        "contact_number",
        "address",
    }

    def post(self, request, *args, **kwargs):
        self.object = None
        if "import_submit" in request.POST:
            return self.handle_import_submission()
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Alumni record created successfully.")
        return super().form_valid(form)

    def get_import_form(self):
        return self.import_form_class()

    def handle_import_submission(self):
        form = self.get_form()
        import_form = self.import_form_class(self.request.POST, self.request.FILES)

        if import_form.is_valid():
            try:
                created_count, updated_count = self.import_alumni_workbook(
                    import_form.cleaned_data["excel_file"]
                )
            except ValidationError as error:
                for message in error.messages:
                    import_form.add_error("excel_file", message)
            else:
                summary = [f"{created_count} added"]
                if updated_count:
                    summary.append(f"{updated_count} updated")
                messages.success(
                    self.request,
                    f"Excel import completed successfully: {', '.join(summary)}.",
                )
                return redirect("accounts:alumni_list")

        return self.render_to_response(self.get_context_data(form=form, import_form=import_form))

    def import_alumni_workbook(self, excel_file):
        try:
            workbook_rows = load_first_sheet_rows(excel_file)
        except WorkbookReadError as error:
            raise ValidationError(str(error)) from error

        if not workbook_rows:
            raise ValidationError("The uploaded Excel file is empty.")

        header_map = self.build_import_header_map(workbook_rows[0])
        data_rows = workbook_rows[1:]

        if not any(any((cell or "").strip() for cell in row) for row in data_rows):
            raise ValidationError("The uploaded Excel file does not contain any alumni rows.")

        program_lookup = self.build_program_lookup()
        row_errors = []
        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for row_number, raw_row in enumerate(data_rows, start=2):
                row_data = self.extract_import_row(raw_row, header_map)
                if not any(value for value in row_data.values()):
                    continue

                normalized_course_program = self.resolve_program_value(
                    row_data.get("course_program", ""),
                    program_lookup,
                )
                form_data = {
                    "surname": row_data.get("surname", ""),
                    "first_name": row_data.get("first_name", ""),
                    "middle_initial": row_data.get("middle_initial", ""),
                    "id_number": row_data.get("id_number", ""),
                    "batch_year": row_data.get("batch_year", ""),
                    "course_program": normalized_course_program,
                    "email": row_data.get("email", ""),
                    "contact_number": row_data.get("contact_number", ""),
                    "address": row_data.get("address", ""),
                    "employment_status": row_data.get("employment_status", ""),
                    "company_name": row_data.get("company_name", ""),
                    "job_title": row_data.get("job_title", ""),
                    "is_public": "on" if self.parse_import_boolean(row_data.get("is_public", "")) else "",
                }

                existing_alumnus = Alumni.objects.filter(
                    department=self.request.user.department,
                    id_number=form_data["id_number"],
                ).first()
                alumni_form = self.form_class(
                    data=form_data,
                    user=self.request.user,
                    instance=existing_alumnus,
                )

                if not alumni_form.is_valid():
                    error_messages = []
                    for field_errors in alumni_form.errors.values():
                        error_messages.extend(field_errors)
                    row_errors.append(f"Row {row_number}: {' '.join(error_messages)}")
                    continue

                alumni_form.save()
                if existing_alumnus is None:
                    created_count += 1
                else:
                    updated_count += 1

            if row_errors:
                raise ValidationError(row_errors)

        return created_count, updated_count

    def build_import_header_map(self, header_row):
        normalized_headers = {}

        for index, cell in enumerate(header_row):
            normalized_header = self.normalize_import_value(cell).lower().replace("-", "_")
            normalized_header = " ".join(normalized_header.split())
            canonical_header = self.IMPORT_HEADER_ALIASES.get(normalized_header)
            if canonical_header:
                normalized_headers[canonical_header] = index

        missing_headers = sorted(self.REQUIRED_IMPORT_COLUMNS - set(normalized_headers))
        if missing_headers:
            display_headers = ", ".join(missing_headers)
            raise ValidationError(
                f"The Excel file is missing required columns: {display_headers}."
            )

        return normalized_headers

    def extract_import_row(self, raw_row, header_map):
        extracted = {}
        for header, index in header_map.items():
            value = raw_row[index] if index < len(raw_row) else ""
            extracted[header] = self.normalize_import_value(value)
        return extracted

    def build_program_lookup(self):
        lookup = {}
        programs = Program.objects.filter(department=self.request.user.department).order_by("program_name")
        for program in programs:
            lookup[self.normalize_import_value(str(program)).casefold()] = str(program)
            lookup[self.normalize_import_value(program.program_code).casefold()] = str(program)
            lookup[self.normalize_import_value(program.program_name).casefold()] = str(program)
        return lookup

    def resolve_program_value(self, raw_value, program_lookup):
        normalized_value = self.normalize_import_value(raw_value)
        return program_lookup.get(normalized_value.casefold(), normalized_value)

    @staticmethod
    def normalize_import_value(value):
        text = str(value or "").strip()
        if text.endswith(".0") and text.replace(".", "", 1).isdigit():
            return text[:-2]
        return text

    @staticmethod
    def parse_import_boolean(value):
        return str(value or "").strip().casefold() in {"1", "true", "yes", "y", "public"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Add Alumni"
        context["page_title"] = "Add Alumni Record"
        context["page_description"] = "Create an alumni record with public and private information kept separate by the interface."
        context["submit_label"] = "Create Alumni Record"
        context["show_photo_field"] = False
        context["import_form"] = kwargs.get("import_form") or self.get_import_form()
        context["import_column_help"] = self.IMPORT_COLUMN_HELP
        return context


class AlumniUpdateView(AlumniFormMixin, UpdateView):
    template_name = "accounts/alumni_form.html"

    def get_queryset(self):
        return self.get_alumni_queryset()

    def form_valid(self, form):
        messages.success(self.request, "Alumni record updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Edit Alumni"
        context["page_title"] = f"Edit {self.object.full_name}"
        context["page_description"] = "Update the alumni profile, private contact details, and public visibility settings."
        context["submit_label"] = "Save Changes"
        context["show_photo_field"] = True
        return context


class AlumniDeleteView(AlumniAccessMixin, DeleteView):
    template_name = "accounts/alumni_confirm_delete.html"
    success_url = reverse_lazy("accounts:alumni_list")

    def get_queryset(self):
        return self.get_alumni_queryset()

    def form_valid(self, form):
        messages.success(self.request, "Alumni record deleted successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Delete Alumni"
        context["page_title"] = f"Delete {self.object.full_name}"
        context["page_description"] = "This action removes the selected alumni record."
        return context


class DepartmentAdminDashboardView(DepartmentAdminRequiredMixin, TemplateView):
    template_name = "accounts/department_admin_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        department = self.request.user.department
        now = timezone.now()
        announcement_count = Announcement.objects.filter(department=department).count()
        news_count = News.objects.filter(department=department).count()
        event_count = Event.objects.filter(department=department).count()
        alumni_count = Alumni.objects.filter(department=department).count()
        program_count = Program.objects.filter(department=department).count()
        instructor_count = Instructor.objects.filter(department=department).count()
        latest_announcements = Announcement.objects.filter(department=department).order_by("-date_posted")[:3]
        latest_news = News.objects.filter(department=department).order_by("-date_posted")[:3]
        recent_updates = build_updates_collection(list(latest_announcements), list(latest_news))[:4]
        upcoming_events = list(
            Event.objects.filter(department=department, event_date__gte=now).order_by("event_date", "-date_posted")[:3]
        )
        if not upcoming_events:
            upcoming_events = list(
                Event.objects.filter(department=department).order_by("-event_date", "-date_posted")[:3]
            )
        recent_instructors = list(
            Instructor.objects.filter(department=department).order_by("-pk")[:3]
        )

        context["dashboard_title"] = f"{department.name} Dashboard"
        context["department"] = department
        context["overview_stats"] = [
            {
                "label": "Programs",
                "value": program_count,
                "icon": "programs",
                "tone": "info",
                "caption": "Academic offerings",
            },
            {
                "label": "Instructors",
                "value": instructor_count,
                "icon": "instructors",
                "tone": "success",
                "caption": "Faculty profiles",
            },
            {
                "label": "Updates",
                "value": announcement_count + news_count,
                "icon": "updates",
                "tone": "alert",
                "caption": "Published notices",
            },
            {
                "label": "Events",
                "value": event_count,
                "icon": "events",
                "tone": "accent",
                "caption": "Scheduled activities",
            },
            {
                "label": "Alumni",
                "value": alumni_count,
                "icon": "alumni",
                "tone": "neutral",
                "caption": "Record visibility",
            },
        ]
        context["management_actions"] = [
            {
                "title": "Manage Programs",
                "detail": "Create and update programs for your department.",
                "url": reverse("accounts:program_list"),
                "icon": "programs",
                "button_label": "Open",
            },
            {
                "title": "Manage Instructors",
                "detail": "Maintain faculty profiles shown on the public page.",
                "url": reverse("accounts:instructor_list"),
                "icon": "instructors",
                "button_label": "Open",
            },
            {
                "title": "Manage Updates",
                "detail": "Publish announcements and news from one workspace.",
                "url": reverse("accounts:update_list"),
                "icon": "updates",
                "button_label": "Open",
            },
            {
                "title": "Manage Events",
                "detail": "Create and organize events shown on the public site.",
                "url": reverse("accounts:event_list"),
                "icon": "events",
                "button_label": "Open",
            },
            {
                "title": "Manage Alumni",
                "detail": "Update alumni records and public visibility.",
                "url": reverse("accounts:alumni_list"),
                "icon": "alumni",
                "button_label": "Open",
            },
            {
                "title": "Edit Department Profile",
                "detail": "Update your mission, vision, leadership details, and banner for the public page.",
                "url": reverse("accounts:department_leadership_update"),
                "icon": "dean",
                "button_label": "Edit",
            },
        ]
        context["quick_actions"] = [
            {
                "title": "Add Program",
                "url": reverse("accounts:program_create"),
                "icon": "programs",
            },
            {
                "title": "Add Instructor",
                "url": reverse("accounts:instructor_create"),
                "icon": "instructors",
            },
            {
                "title": "Create Event",
                "url": reverse("accounts:event_create"),
                "icon": "events",
            },
            {
                "title": "Post Update",
                "url": reverse("accounts:update_create"),
                "icon": "updates",
            },
        ]
        context["recent_updates"] = recent_updates
        context["recent_instructors"] = recent_instructors
        context["upcoming_events"] = upcoming_events
        context["management_sections"] = [
            {
                "title": "Department Overview",
                "description": "Monitor the academic unit profile, branding, and overall public presence.",
            },
            {
                "title": "Academic Records",
                "description": "Review programs and instructor listings tied to your assigned department only.",
            },
            {
                "title": "Department Content",
                "description": "Track updates, events, and alumni data connected to your department.",
            },
        ]
        return context
