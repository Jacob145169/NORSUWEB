from django.shortcuts import render

from content.models import Announcement, Event, News
from departments.models import Department, SchoolInfo


def get_public_site_context(
    *,
    announcement_limit=3,
    featured_news_limit=4,
    news_limit=3,
    event_limit=3,
    exclude_featured_news_from_updates=False,
):
    active_departments = Department.objects.filter(is_active=True).order_by("name")
    active_department_filter = {"department__is_active": True}
    latest_announcements = (
        Announcement.objects.select_related("department", "posted_by")
        .filter(**active_department_filter)
        .order_by("-date_posted")
    )
    latest_news = (
        News.objects.select_related("department", "posted_by")
        .filter(**active_department_filter)
        .order_by("-date_posted")
    )
    latest_events = (
        Event.objects.select_related("department", "posted_by")
        .filter(**active_department_filter)
        .order_by("event_date", "-date_posted")
    )
    featured_news = list(latest_news[:featured_news_limit])
    featured_news_ids = [item.pk for item in featured_news]

    if exclude_featured_news_from_updates and featured_news_ids:
        latest_news = latest_news.exclude(pk__in=featured_news_ids).order_by("-date_posted")

    return {
        "school_info": SchoolInfo.objects.first(),
        "departments": active_departments,
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
            "page_heading": page_heading,
            "page_description": page_description,
            "section_label": section_label,
            "section_title": section_title,
            "page_content": getattr(school_info, content_attr, ""),
            "fallback_content": fallback_content,
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
        exclude_featured_news_from_updates=True,
    )
    return render(request, "core/updates.html", context)
