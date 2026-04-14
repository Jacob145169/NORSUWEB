from pathlib import Path
import re

from django.conf import settings
from django.db.models import Count, Prefetch
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.models import RoleChoices, User
from alumni.models import Alumni
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


def get_landing_background_image_url(school_info):
    if school_info and school_info.landing_background_image:
        return school_info.landing_background_image.url

    if school_info and school_info.history_image:
        return school_info.history_image.url

    return ""


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


def extract_core_values_items(value):
    if not value:
        return []

    normalized_value = normalize_information_text(value)
    if not normalized_value:
        return []

    shine_letters = list("SHINE")
    pattern = re.compile(
        r"(?<!\S)(?P<letter>[A-Za-z])\s*-\s*(?P<title>.+?)(?=(?:\s+[A-Za-z]\s*-\s*)|$)"
    )
    matches = list(pattern.finditer(normalized_value))
    if matches:
        remainder = pattern.sub("", normalized_value)
        if not re.sub(r"[\s|,;:.!?/&()\[\]{}'\"-]+", "", remainder):
            return [
                {
                    "letter": match.group("letter").upper(),
                    "title": match.group("title").strip(),
                }
                for match in matches
            ]

    line_items = [line.strip() for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]
    if len(line_items) > 1:
        return [
            {
                "letter": shine_letters[index] if index < len(shine_letters) else item[:1].upper(),
                "title": item,
            }
            for index, item in enumerate(line_items)
        ]

    paragraph_chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", value) if chunk.strip()]
    if len(paragraph_chunks) > 1:
        return [
            {
                "letter": shine_letters[index] if index < len(shine_letters) else normalize_information_text(chunk)[:1].upper(),
                "title": normalize_information_text(chunk),
            }
            for index, chunk in enumerate(paragraph_chunks)
            if normalize_information_text(chunk)
        ]

    return []


def extract_strategic_goal_content(value):
    if not value:
        return "", []

    normalized_value = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized_value:
        return "", []

    def clean_goal_item(item):
        cleaned_item = re.sub(r"^[\s\-\u2022]+", "", item).strip()
        cleaned_item = re.sub(r"^\d+[\.\)]\s*", "", cleaned_item).strip()
        cleaned_item = re.sub(r"^[A-Za-z][\.\)]\s*", "", cleaned_item).strip()
        return cleaned_item

    def finalize(intro, items):
        cleaned_intro = normalize_information_text(intro) if intro else ""
        cleaned_items = [clean_goal_item(item) for item in items if clean_goal_item(item)]
        if len(cleaned_items) > 1:
            return cleaned_intro, cleaned_items
        return "", []

    paragraph_chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", normalized_value) if chunk.strip()]
    if len(paragraph_chunks) > 1:
        if paragraph_chunks[0].endswith(":"):
            return finalize(paragraph_chunks[0], paragraph_chunks[1:])
        return finalize("", [normalize_information_text(chunk) for chunk in paragraph_chunks if normalize_information_text(chunk)])

    line_items = [line.strip() for line in normalized_value.split("\n") if line.strip()]
    if len(line_items) > 1:
        if line_items[0].endswith(":"):
            return finalize(line_items[0], line_items[1:])
        return finalize("", line_items)

    if normalized_value.count(" - ") >= 2:
        intro_candidate, remainder = normalized_value.split(" - ", 1)
        dash_inline_items = [item.strip() for item in remainder.split(" - ") if item.strip()]
        if len(dash_inline_items) > 1:
            intro = intro_candidate.strip() if intro_candidate.strip().endswith(":") else ""
            items = dash_inline_items if intro else [intro_candidate.strip(), *dash_inline_items]
            return finalize(intro, items)

    inline_pattern = re.compile(
        r"(?:^|\s)(?:\d+[\.\)]|[A-Za-z][\.\)])\s*(.+?)(?=(?:\s+(?:\d+[\.\)]|[A-Za-z][\.\)])\s*)|$)"
    )
    inline_matches = [match.group(1).strip() for match in inline_pattern.finditer(normalized_value) if match.group(1).strip()]
    if len(inline_matches) > 1:
        first_match = inline_pattern.search(normalized_value)
        intro = normalized_value[:first_match.start()].strip(" \n\r\t:-") if first_match else ""
        if intro:
            intro = f"{intro}:"
        return finalize(intro, inline_matches)

    return "", []


def build_strategic_goal_cards(items):
    aspire_letters = list("ASPIRE")
    cards = []

    for index, item in enumerate(items):
        badge = aspire_letters[index] if index < len(aspire_letters) else str(index + 1)
        cards.append(
            {
                "badge": badge,
                "text": item,
            }
        )

    return cards


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
    strategic_goal_intro = ""
    strategic_goal_items = []
    raw_page_content = getattr(school_info, content_attr, "")
    if browser_title == "Strategic Goals":
        strategic_goal_intro, strategic_goal_items = extract_strategic_goal_content(raw_page_content)
    page_content = (
        normalize_history_text(raw_page_content)
        if browser_title == "History"
        else normalize_information_text(raw_page_content)
    )
    context.update(
        {
            "browser_title": browser_title,
            "is_history_page": browser_title == "History",
            "is_core_values_page": browser_title == "Core Values",
            "is_strategic_goals_page": browser_title == "Strategic Goals",
            "page_heading": page_heading,
            "page_description": page_description,
            "section_label": section_label,
            "section_title": section_title,
            "page_content": page_content,
            "core_values_items": extract_core_values_items(raw_page_content) if browser_title == "Core Values" else [],
            "strategic_goal_intro": strategic_goal_intro,
            "strategic_goal_items": strategic_goal_items,
            "strategic_goal_cards": build_strategic_goal_cards(strategic_goal_items) if browser_title == "Strategic Goals" else [],
            "fallback_content": fallback_content,
            "history_image_url": get_history_image_url(school_info) if browser_title == "History" else "",
        }
    )
    return render(request, "core/info_page.html", context)


def build_about_page_context():
    context = get_public_site_context(
        announcement_limit=0,
        featured_news_limit=0,
        news_limit=0,
        event_limit=0,
    )
    school_info = context["school_info"]
    strategic_goal_intro, strategic_goal_items = extract_strategic_goal_content(
        getattr(school_info, "strategic_goals", "")
    )
    context.update(
        {
            "browser_title": "About",
            "page_heading": "About NORSU",
            "page_description": (
                "Explore the university's history, mission and vision, strategic goals, core values, "
                "quality policy, and official calendar in one place."
            ),
            "history_content": normalize_information_text(getattr(school_info, "history", "")),
            "history_fallback": (
                "Negros Oriental State University continues to build on its educational heritage "
                "by serving learners across diverse disciplines and communities."
            ),
            "history_image_url": get_history_image_url(school_info),
            "mission_content": normalize_information_text(getattr(school_info, "mission", "")),
            "mission_fallback": (
                "Negros Oriental State University is committed to delivering quality education, "
                "responsive research, and meaningful community engagement."
            ),
            "vision_content": normalize_information_text(getattr(school_info, "vision", "")),
            "vision_fallback": (
                "The university envisions a vibrant academic community producing competent, "
                "ethical, and globally engaged graduates."
            ),
            "strategic_goal_intro": strategic_goal_intro,
            "strategic_goal_items": strategic_goal_items,
            "strategic_goal_cards": build_strategic_goal_cards(strategic_goal_items),
            "strategic_goals_content": normalize_information_text(getattr(school_info, "strategic_goals", "")),
            "strategic_goals_fallback": (
                "The university's strategic goals outline the priority outcomes that guide "
                "planning, academic excellence, and community impact."
            ),
            "core_values_items": extract_core_values_items(getattr(school_info, "core_values", "")),
            "core_values_content": normalize_information_text(getattr(school_info, "core_values", "")),
            "core_values_fallback": (
                "The university's core values guide ethical leadership, academic integrity, "
                "and service to the wider community."
            ),
            "quality_policy_content": normalize_information_text(getattr(school_info, "quality_policy", "")),
            "quality_policy_fallback": (
                "The university's quality policy affirms its commitment to continuous improvement, "
                "reliable public service, and learner-centered excellence."
            ),
            "calendar_images": school_info.calendar_images.all() if school_info else [],
        }
    )
    return context


def redirect_to_about_section(section_id):
    return redirect(f"{reverse('core:about')}#{section_id}")


def home(request):
    context = get_public_site_context(news_limit=0)
    context["latest_updates"] = build_public_updates_collection(
        list(context["latest_announcements"]),
        list(context["featured_news"]),
    )
    context["landing_background_image_url"] = get_landing_background_image_url(context["school_info"])
    context["home_intro_phrases"] = ["OUR PRIDE", "OUR HOPE", "OUR FUTURE"]
    return render(request, "core/home.html", context)


def mission(request):
    return redirect_to_about_section("mission-vision")


def vision(request):
    return redirect_to_about_section("mission-vision")


def about(request):
    return render(request, "core/about.html", build_about_page_context())


def mission_vision(request):
    return redirect_to_about_section("mission-vision")


def strategic_goals(request):
    return redirect_to_about_section("strategic-goals")


def core_values(request):
    return redirect_to_about_section("core-values")


def quality_policy(request):
    return redirect_to_about_section("quality-policy")


def history(request):
    return redirect_to_about_section("history")


def calendar(request):
    return redirect_to_about_section("calendar")


def contact(request):
    context = get_public_site_context(
        announcement_limit=0,
        featured_news_limit=0,
        news_limit=0,
        event_limit=0,
    )
    context.update(
        {
            "browser_title": "Contact",
            "page_heading": "Contact NORSU",
            "page_description": (
                "Find the campus address, official email, and phone number for "
                "NORSU Bayawan-Sta. Catalina Campus."
            ),
            "contact_items": [
                {
                    "label": "Campus address",
                    "value": "Bayawan City, Negros Oriental",
                    "href": "",
                    "description": "Visit the Bayawan-Sta. Catalina Campus for on-site assistance and public inquiries.",
                },
                {
                    "label": "Email address",
                    "value": "norsu@email.com",
                    "href": "mailto:norsu@email.com",
                    "description": "Send general questions, requests, and official communications through email.",
                },
                {
                    "label": "Phone number",
                    "value": "+63 912 345 6789",
                    "href": "tel:+639123456789",
                    "description": "Call the campus office for immediate assistance during office hours.",
                },
            ],
        }
    )
    return render(request, "core/contact.html", context)


def alumni(request):
    context = get_public_site_context(
        announcement_limit=0,
        featured_news_limit=0,
        news_limit=0,
        event_limit=0,
    )

    selected_department = (request.GET.get("department") or "").strip()
    selected_batch = (request.GET.get("batch") or "").strip()
    department_options = (
        Department.objects.filter(is_active=True, alumni__is_public=True)
        .annotate(public_alumni_count=Count("alumni", filter=Q(alumni__is_public=True)))
        .order_by("name")
        .distinct()
    )
    base_public_alumni = Alumni.objects.select_related("department").filter(
        is_public=True,
        department__is_active=True,
    ).order_by("-batch_year", "full_name")
    public_alumni = base_public_alumni.none()
    selected_department_object = None

    if selected_department:
        selected_department_object = department_options.filter(pk=selected_department).first()
        if selected_department_object is not None:
            public_alumni = base_public_alumni.filter(department=selected_department_object)
        else:
            selected_department = ""

    batch_options = list(
        public_alumni.order_by("-batch_year")
        .values_list("batch_year", flat=True)
        .distinct()
    )

    if selected_department_object is not None and selected_batch.isdigit():
        public_alumni = public_alumni.filter(batch_year=int(selected_batch))
    else:
        selected_batch = ""

    context.update(
        {
            "browser_title": "Alumni",
            "selected_department": selected_department,
            "selected_batch": selected_batch,
            "selected_department_name": selected_department_object.name if selected_department_object else "",
            "department_options": department_options,
            "batch_options": batch_options,
            "public_alumni": public_alumni,
        }
    )
    return render(request, "core/alumni.html", context)


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
