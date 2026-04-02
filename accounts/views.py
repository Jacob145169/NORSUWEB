from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, RedirectView, TemplateView, UpdateView

from .forms import (
    AdminAuthenticationForm,
    AlumniForm,
    AnnouncementForm,
    DepartmentAdminCreationForm,
    DepartmentAdminUpdateForm,
    DepartmentForm,
    EventForm,
    InstructorForm,
    NewsForm,
    ProgramForm,
    SchoolInfoForm,
)
from .models import RoleChoices, User
from .permissions import (
    DepartmentAdminRequiredMixin,
    DepartmentScopedQuerysetMixin,
    PortalLoginRequiredMixin,
    SuperAdminRequiredMixin,
)
from .view_mixins import PageMetadataMixin, SuccessMessageMixin, UserFormKwargsMixin
from academics.models import Instructor, Program
from alumni.models import Alumni
from content.models import Announcement, Event, News
from departments.models import Department, SchoolInfo


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


class AnnouncementAccessMixin(DepartmentScopedQuerysetMixin):
    model = Announcement

    def get_announcement_queryset(self):
        queryset = Announcement.objects.select_related("department", "posted_by").order_by("-date_posted")
        return self.scope_to_user_department(queryset)


class AnnouncementFormMixin(UserFormKwargsMixin, AnnouncementAccessMixin):
    form_class = AnnouncementForm

    def form_valid(self, form):
        form.instance.posted_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("accounts:announcement_list")


class NewsAccessMixin(DepartmentScopedQuerysetMixin):
    model = News

    def get_news_queryset(self):
        queryset = News.objects.select_related("department", "posted_by").order_by("-date_posted")
        return self.scope_to_user_department(queryset)


class NewsFormMixin(UserFormKwargsMixin, NewsAccessMixin):
    form_class = NewsForm

    def form_valid(self, form):
        form.instance.posted_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("accounts:news_list")


class EventAccessMixin(DepartmentScopedQuerysetMixin):
    model = Event

    def get_event_queryset(self):
        queryset = Event.objects.select_related("department", "posted_by").order_by("event_date", "-date_posted")
        return self.scope_to_user_department(queryset)


class EventFormMixin(UserFormKwargsMixin, EventAccessMixin):
    form_class = EventForm

    def form_valid(self, form):
        form.instance.posted_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("accounts:event_list")


class AlumniAccessMixin(DepartmentScopedQuerysetMixin):
    model = Alumni

    def get_alumni_queryset(self):
        queryset = Alumni.objects.select_related("department").order_by("-batch_year", "full_name")
        return self.scope_to_user_department(queryset)


class AlumniFormMixin(UserFormKwargsMixin, AlumniAccessMixin):
    form_class = AlumniForm

    def get_success_url(self):
        return reverse("accounts:alumni_list")


class SuperAdminDashboardView(SuperAdminRequiredMixin, TemplateView):
    template_name = "accounts/super_admin_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Super Admin Dashboard"
        context["overview_stats"] = [
            {"label": "Total Departments", "value": Department.objects.count()},
            {"label": "Total Programs", "value": Program.objects.count()},
            {"label": "Total Instructors", "value": Instructor.objects.count()},
            {"label": "Total Announcements", "value": Announcement.objects.count()},
            {"label": "Total News", "value": News.objects.count()},
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
                    "Manage all announcements, news, and events",
                    "Manage all alumni records",
                ],
            },
        ]
        context["quick_links"] = [
            {"title": "Landing Page Content", "detail": "School information and homepage sections", "url": reverse("accounts:school_info_update")},
            {"title": "Departments", "detail": "Create and organize department records", "url": reverse("accounts:department_list")},
            {"title": "Department Admin Accounts", "detail": "Manage department-level administrator access", "url": reverse("accounts:department_admin_list")},
            {"title": "Programs", "detail": "Oversee all academic programs", "url": reverse("accounts:program_list")},
            {"title": "Instructors", "detail": "Maintain instructor profiles", "url": reverse("accounts:instructor_list")},
            {"title": "Announcements", "detail": "Manage public announcements", "url": reverse("accounts:announcement_list")},
            {"title": "News", "detail": "Manage news content", "url": reverse("accounts:news_list")},
            {"title": "Events", "detail": "Manage public events", "url": reverse("accounts:event_list")},
            {"title": "Alumni", "detail": "Maintain alumni records and public visibility", "url": reverse("accounts:alumni_list")},
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
    dashboard_title = "Edit Landing Page Content"
    page_title = "Edit School Information"
    page_description = "Update the college name, mission, vision, and history used on the public landing page."
    success_message = "Landing page content has been updated successfully."

    def get_object(self, queryset=None):
        school_info, _ = SchoolInfo.objects.get_or_create(
            pk=1,
            defaults={
                "college_name": "Negros Oriental State University",
                "mission": "",
                "vision": "",
                "history": "",
            },
        )
        return school_info

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


class AnnouncementListView(AnnouncementAccessMixin, ListView):
    template_name = "accounts/announcement_list.html"
    context_object_name = "announcements"

    def get_queryset(self):
        return self.get_announcement_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.role == RoleChoices.SUPER_ADMIN:
            context["dashboard_title"] = "Announcement Management"
            context["page_title"] = "Announcement Management"
            context["page_description"] = "Manage announcements across all departments."
        else:
            context["dashboard_title"] = f"{user.department.name} Announcements"
            context["page_title"] = "Department Announcement Management"
            context["page_description"] = f"Manage announcements for {user.department.name} only."

        return context


class AnnouncementCreateView(AnnouncementFormMixin, CreateView):
    template_name = "accounts/announcement_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Announcement created successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Add Announcement"
        context["page_title"] = "Add Announcement"
        context["page_description"] = "Create a new announcement for the public site."
        context["submit_label"] = "Create Announcement"
        return context


class AnnouncementUpdateView(AnnouncementFormMixin, UpdateView):
    template_name = "accounts/announcement_form.html"

    def get_queryset(self):
        return self.get_announcement_queryset()

    def form_valid(self, form):
        messages.success(self.request, "Announcement updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Edit Announcement"
        context["page_title"] = f"Edit {self.object.title}"
        context["page_description"] = "Update the announcement content, image, and department assignment."
        context["submit_label"] = "Save Changes"
        return context


class AnnouncementDeleteView(AnnouncementAccessMixin, DeleteView):
    template_name = "accounts/announcement_confirm_delete.html"
    success_url = reverse_lazy("accounts:announcement_list")

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


class NewsListView(NewsAccessMixin, ListView):
    template_name = "accounts/news_list.html"
    context_object_name = "news_items"

    def get_queryset(self):
        return self.get_news_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.role == RoleChoices.SUPER_ADMIN:
            context["dashboard_title"] = "News Management"
            context["page_title"] = "News Management"
            context["page_description"] = "Manage news entries across all departments."
        else:
            context["dashboard_title"] = f"{user.department.name} News"
            context["page_title"] = "Department News Management"
            context["page_description"] = f"Manage news entries for {user.department.name} only."

        return context


class NewsCreateView(NewsFormMixin, CreateView):
    template_name = "accounts/news_form.html"

    def form_valid(self, form):
        messages.success(self.request, "News entry created successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Add News"
        context["page_title"] = "Add News"
        context["page_description"] = "Create a news entry for the public site."
        context["submit_label"] = "Create News"
        return context


class NewsUpdateView(NewsFormMixin, UpdateView):
    template_name = "accounts/news_form.html"

    def get_queryset(self):
        return self.get_news_queryset()

    def form_valid(self, form):
        messages.success(self.request, "News entry updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Edit News"
        context["page_title"] = f"Edit {self.object.title}"
        context["page_description"] = "Update the news content, image, and department assignment."
        context["submit_label"] = "Save Changes"
        return context


class NewsDeleteView(NewsAccessMixin, DeleteView):
    template_name = "accounts/news_confirm_delete.html"
    success_url = reverse_lazy("accounts:news_list")

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

    def form_valid(self, form):
        messages.success(self.request, "Event created successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Add Event"
        context["page_title"] = "Add Event"
        context["page_description"] = "Create an event entry for the public site."
        context["submit_label"] = "Create Event"
        return context


class EventUpdateView(EventFormMixin, UpdateView):
    template_name = "accounts/event_form.html"

    def get_queryset(self):
        return self.get_event_queryset()

    def form_valid(self, form):
        messages.success(self.request, "Event updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Edit Event"
        context["page_title"] = f"Edit {self.object.title}"
        context["page_description"] = "Update the event details, schedule, image, and department assignment."
        context["submit_label"] = "Save Changes"
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

    def get_queryset(self):
        return self.get_alumni_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.role == RoleChoices.SUPER_ADMIN:
            context["dashboard_title"] = "Alumni Management"
            context["page_title"] = "Alumni Management"
            context["page_description"] = "Manage alumni records and public visibility across all departments."
        else:
            context["dashboard_title"] = f"{user.department.name} Alumni"
            context["page_title"] = "Department Alumni Management"
            context["page_description"] = f"Manage alumni records for {user.department.name} only."

        return context


class AlumniCreateView(AlumniFormMixin, CreateView):
    template_name = "accounts/alumni_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Alumni record created successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_title"] = "Add Alumni"
        context["page_title"] = "Add Alumni Record"
        context["page_description"] = "Create an alumni record with public and private information kept separate by the interface."
        context["submit_label"] = "Create Alumni Record"
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
        context["dashboard_title"] = f"{department.name} Dashboard"
        context["department"] = department
        context["overview_stats"] = [
            {"label": "Programs", "value": Program.objects.filter(department=department).count()},
            {"label": "Instructors", "value": Instructor.objects.filter(department=department).count()},
            {"label": "Announcements", "value": Announcement.objects.filter(department=department).count()},
            {"label": "News", "value": News.objects.filter(department=department).count()},
            {"label": "Events", "value": Event.objects.filter(department=department).count()},
            {"label": "Alumni", "value": Alumni.objects.filter(department=department).count()},
        ]
        context["programs"] = Program.objects.filter(department=department).order_by("program_name")[:6]
        context["instructors"] = Instructor.objects.filter(department=department).order_by("full_name")[:6]
        context["announcements"] = Announcement.objects.filter(department=department).order_by("-date_posted")[:5]
        context["news_items"] = News.objects.filter(department=department).order_by("-date_posted")[:5]
        context["events"] = Event.objects.filter(department=department).order_by("event_date")[:5]
        context["alumni_items"] = Alumni.objects.filter(department=department).order_by("-batch_year", "full_name")[:6]
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
                "description": "Track announcements, news, events, and alumni data connected to your department.",
            },
        ]
        return context
