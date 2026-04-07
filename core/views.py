from pathlib import Path
import re

from django.conf import settings
from django.db.models import Prefetch
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from accounts.models import RoleChoices, User
from content.models import Announcement, Event, News, PublicationStatus
from departments.models import Department, SchoolInfo


DEFAULT_HISTORY_IMAGE_RELATIVE_PATH = Path("content/images/history_pic.jpg")


def get_public_updates_filter():
    return (
        (Q(department__is_active=True) | Q(department__isnull=True))
        & Q(publication_status=PublicationStatus.PUBLISHED)
    )


def build_public_updates_collection(announcements, news_items):
    updates = []

    for announcement in announcements:
        announcement.update_kind = "Announcement"
        announcement.update_type = "announcement"
        updates.append(announcement)

    for item in news_items:
        item.update_kind = "News"
        item.update_type = "news"
        updates.append(item)

    updates.sort(key=lambda item: item.date_posted, reverse=True)
    return updates


def get_history_image_url(school_info):
    if school_info and school_info.history_image:
        return school_info.history_image.url

    default_history_image = Path(settings.MEDIA_ROOT) / DEFAULT_HISTORY_IMAGE_RELATIVE_PATH
    if not default_history_image.exists():
        return ""

    media_url = settings.MEDIA_URL
    if not media_url.startswith("/"):
        media_url = f"/{media_url}"
    if not media_url.endswith("/"):
        media_url = f"{media_url}/"

    return f"{media_url}{DEFAULT_HISTORY_IMAGE_RELATIVE_PATH.as_posix()}"


def normalize_information_text(value):
    if not value:
        return ""

    normalized_value = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    paragraph_chunks = re.split(r"\n\s*\n", normalized_value)
    paragraphs = []

    for chunk in paragraph_chunks:
        lines = [line.strip() for line in chunk.split("\n") if line.strip()]
        if lines:
            paragraphs.append(" ".join(lines))

    return "\n\n".join(paragraphs)


def normalize_history_text(value):
    if not value:
        return ""

    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def get_public_site_context(
    *,
    announcement_limit=3,
    featured_news_limit=4,
    news_limit=3,
    event_limit=3,
    exclude_featured_news_from_updates=False,
):
    department_admin_prefetch = Prefetch(
        "users",
        queryset=User.objects.filter(role=RoleChoices.DEPARTMENT_ADMIN, is_active=True).order_by("full_name"),
        to_attr="department_admin_accounts",
    )
    active_departments = Department.objects.filter(is_active=True).prefetch_related(department_admin_prefetch).order_by("name")
    featured_department_ids = User.objects.filter(
        role=RoleChoices.DEPARTMENT_ADMIN,
        is_active=True,
        department__is_active=True,
    ).values_list("department_id", flat=True)
    featured_departments = list(active_departments.filter(pk__in=featured_department_ids)[:6])
    public_updates_filter = get_public_updates_filter()
    latest_announcements = (
        Announcement.objects.select_related("department", "posted_by")
        .filter(public_updates_filter)
        .order_by("-date_posted")
    )
    latest_news = (
        News.objects.select_related("department", "posted_by")
        .filter(public_updates_filter)
        .order_by("-date_posted")
    )
    latest_events = (
        Event.objects.select_related("department", "posted_by")
        .filter(public_updates_filter, publication_status=PublicationStatus.PUBLISHED)
        .order_by("event_date", "-date_posted")
    )
    featured_news = list(latest_news[:featured_news_limit])
    featured_news_ids = [item.pk for item in featured_news]

    if exclude_featured_news_from_updates and featured_news_ids:
        latest_news = latest_news.exclude(pk__in=featured_news_ids).order_by("-date_posted")

    return {
        "school_info": SchoolInfo.get_solo(),
        "departments": active_departments,
        "featured_departments": featured_departments,
        "latest_announcements": latest_announcements[:announcement_limit],
        "featured_news": featured_news,
        "latest_news": latest_news[:news_limit],
        "latest_events": latest_events[:event_limit],
    }


def render_information_page(
    request,
    *,
    browser_title,
    page_heading,
    page_description,
    section_label,
    section_title,
    content_attr,
    fallback_content,
):
    context = get_public_site_context()
    school_info = context["school_info"]
    context.update(
        {
            "browser_title": browser_title,
            "is_history_page": browser_title == "History",
            "page_heading": page_heading,
            "page_description": page_description,
            "section_label": section_label,
            "section_title": section_title,
            "page_content": (
                normalize_history_text(getattr(school_info, content_attr, ""))
                if browser_title == "History"
                else normalize_information_text(getattr(school_info, content_attr, ""))
            ),
            "fallback_content": fallback_content,
            "history_image_url": get_history_image_url(school_info) if browser_title == "History" else "",
        }
    )
    return render(request, "core/info_page.html", context)


def home(request):
    context = get_public_site_context(news_limit=0)
    return render(request, "core/home.html", context)


def mission(request):
    return render_information_page(
        request,
        browser_title="Mission",
        page_heading="University mission",
        page_description="Learn about the institutional purpose that guides teaching, research, and public service across the university.",
        section_label="Mission",
        section_title="Institutional purpose",
        content_attr="mission",
        fallback_content=(
            "Negros Oriental State University is committed to delivering quality education, "
            "responsive research, and meaningful community engagement."
        ),
    )


def vision(request):
    return render_information_page(
        request,
        browser_title="Vision",
        page_heading="University vision",
        page_description="See the long-term direction that shapes the university's aspirations for students, faculty, and the wider community.",
        section_label="Vision",
        section_title="Long-term direction",
        content_attr="vision",
        fallback_content=(
            "The university envisions a vibrant academic community producing competent, "
            "ethical, and globally engaged graduates."
        ),
    )


def history(request):
    return render_information_page(
        request,
        browser_title="History",
        page_heading="University history",
        page_description="Explore the institutional story, milestones, and academic legacy that continue to shape NORSU today.",
        section_label="History",
        section_title="A growing academic tradition",
        content_attr="history",
        fallback_content=(
            "Negros Oriental State University continues to build on its educational heritage "
            "by serving learners across diverse disciplines and communities."
        ),
    )


def updates(request):
    context = get_public_site_context(
        announcement_limit=6,
        news_limit=6,
        event_limit=6,
    )
    context["latest_updates"] = build_public_updates_collection(
        list(context["latest_announcements"]),
        list(context["latest_news"]),
    )
    return render(request, "core/updates.html", context)


def update_detail(request, update_type, pk):
    if update_type == "announcement":
        model = Announcement
        update_kind = "Announcement"
    elif update_type == "news":
        model = News
        update_kind = "News"
    else:
        raise Http404("Update type not found.")

    update_item = get_object_or_404(
        model.objects.select_related("department", "posted_by").filter(get_public_updates_filter()),
        pk=pk,
    )
    context = get_public_site_context()
    context.update(
        {
            "browser_title": update_item.title,
            "update_item": update_item,
            "update_kind": update_kind,
            "update_type": update_type,
        }
    )
    return render(request, "core/update_detail.html", context)


def event_detail(request, pk):
    event = get_object_or_404(
        Event.objects.select_related("department", "posted_by").filter(get_public_updates_filter()),
        pk=pk,
    )
    context = get_public_site_context()
    context.update(
        {
            "browser_title": event.title,
            "event": event,
        }
    )
    return render(request, "core/event_detail.html", context)
