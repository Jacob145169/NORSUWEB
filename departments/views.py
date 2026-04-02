from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render

from academics.models import Instructor, Program
from alumni.models import Alumni
from content.models import Announcement, Event, News
from .models import Department, SchoolInfo


def department_list(request):
    context = {
        "departments": Department.objects.filter(is_active=True).order_by("name"),
        "school_info": SchoolInfo.objects.first(),
    }
    return render(request, "departments/list.html", context)


def department_detail(request, slug):
    department = get_object_or_404(
        Department.objects.prefetch_related(
            Prefetch("programs", queryset=Program.objects.order_by("program_name")),
            Prefetch("instructors", queryset=Instructor.objects.order_by("full_name")),
            Prefetch(
                "announcements",
                queryset=Announcement.objects.select_related("posted_by").order_by("-date_posted"),
            ),
            Prefetch(
                "news",
                queryset=News.objects.select_related("posted_by").order_by("-date_posted"),
            ),
            Prefetch(
                "events",
                queryset=Event.objects.select_related("posted_by").order_by("event_date", "-date_posted"),
            ),
            Prefetch(
                "alumni",
                queryset=Alumni.objects.filter(is_public=True).order_by("-batch_year", "full_name"),
            ),
        ),
        slug=slug,
        is_active=True,
    )
    context = {
        "department": department,
        "programs": department.programs.all(),
        "instructors": department.instructors.all(),
        "announcements": department.announcements.all()[:6],
        "news_items": department.news.all()[:6],
        "events": department.events.all()[:6],
        "public_alumni": department.alumni.all()[:8],
    }
    return render(request, "departments/detail.html", context)
