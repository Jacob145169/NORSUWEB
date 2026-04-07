from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render

from accounts.models import RoleChoices, User
from academics.models import Instructor, Program
from alumni.models import Alumni
from content.models import Announcement, Event, News, PublicationStatus
from .models import Department, SchoolInfo


def department_list(request):
    context = {
        "departments": Department.objects.filter(is_active=True).order_by("name"),
        "school_info": SchoolInfo.get_solo(),
    }
    return render(request, "departments/list.html", context)


def department_detail(request, slug):
    department = get_object_or_404(
        Department.objects.prefetch_related(
            Prefetch(
                "users",
                queryset=User.objects.filter(role=RoleChoices.DEPARTMENT_ADMIN, is_active=True).order_by("full_name"),
                to_attr="department_admin_accounts",
            ),
            Prefetch("programs", queryset=Program.objects.order_by("program_name")),
            Prefetch("instructors", queryset=Instructor.objects.order_by("full_name")),
            Prefetch(
                "announcements",
                queryset=Announcement.objects.select_related("posted_by")
                .filter(publication_status=PublicationStatus.PUBLISHED)
                .order_by("-date_posted"),
            ),
            Prefetch(
                "newss",
                queryset=News.objects.select_related("posted_by")
                .filter(publication_status=PublicationStatus.PUBLISHED)
                .order_by("-date_posted"),
            ),
            Prefetch(
                "events",
                queryset=Event.objects.select_related("posted_by")
                .filter(publication_status=PublicationStatus.PUBLISHED)
                .order_by("event_date", "-date_posted"),
            ),
            Prefetch(
                "alumni",
                queryset=Alumni.objects.filter(is_public=True).order_by("-batch_year", "full_name"),
            ),
        ),
        slug=slug,
        is_active=True,
    )
    dean = department.department_admin_accounts[0] if getattr(department, "department_admin_accounts", None) else None
    dean_name = department.dean_name or (
        (dean.full_name or dean.username) if dean else ""
    )
    assistant_dean_name = department.assistant_dean_name
    announcements = list(department.announcements.all()[:6])
    news_items = list(department.newss.all()[:6])

    for announcement in announcements:
        announcement.update_kind = "Announcement"
        announcement.update_type = "announcement"

    for item in news_items:
        item.update_kind = "News"
        item.update_type = "news"

    department_updates = sorted(
        [*announcements, *news_items],
        key=lambda item: item.date_posted,
        reverse=True,
    )

    context = {
        "department": department,
        "dean": dean,
        "dean_name": dean_name,
        "assistant_dean_name": assistant_dean_name,
        "programs": department.programs.all(),
        "instructors": department.instructors.all(),
        "department_updates": department_updates,
        "events": department.events.all()[:6],
        "public_alumni": department.alumni.all()[:8],
    }
    return render(request, "departments/detail.html", context)
