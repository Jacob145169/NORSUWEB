import shutil
from datetime import timedelta
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import RoleChoices, User
from alumni.models import Alumni
from content.models import Announcement, Event, News, PublicationStatus
from departments.models import CalendarImage, Department, SchoolInfo


TEST_GIF = (
    b"GIF87a\x01\x00\x01\x00\x80\x00\x00"
    b"\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"
    b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)
TEST_MEDIA_ROOT = Path(__file__).resolve().parent.parent / ".test_media_core"


def build_test_video(*, name="test.mp4"):
    return SimpleUploadedFile(name, b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41", content_type="video/mp4")


class PublicNewsViewTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="College of Science",
            code="COS",
            description="Science programs and updates.",
            theme_color="#12345b",
            is_active=True,
        )
        self.school_info = SchoolInfo.objects.create(
            college_name="Negros Oriental State University",
            mission="Mission text for the homepage.",
            vision="Vision text for the homepage.",
            strategic_goals="Strategic goals text for the homepage.",
            core_values="Core values text for the homepage.",
            quality_policy="Quality policy text for the homepage.",
            history="History text.",
        )

    def create_news_batch(self, count=6):
        created_items = []
        base_time = timezone.now() - timedelta(days=count)

        for index in range(count):
            item = News.objects.create(
                title=f"News {index}",
                content=f"Content for news item {index}.",
                department=self.department,
            )
            timestamp = base_time + timedelta(days=index)
            News.objects.filter(pk=item.pk).update(date_posted=timestamp)
            item.refresh_from_db()
            created_items.append(item)

        return created_items

    def test_homepage_uses_four_most_recent_news_items_for_carousel(self):
        self.create_news_batch()

        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="homeUpdatesFeaturedCarousel"')
        self.assertEqual(
            [item.title for item in response.context["featured_news"]],
            ["News 5", "News 4", "News 3", "News 2"],
        )

    def test_updates_page_includes_homepage_featured_news_items(self):
        self.create_news_batch()

        response = self.client.get(reverse("core:updates"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item.title for item in response.context["featured_news"]],
            ["News 5", "News 4", "News 3", "News 2"],
        )
        self.assertEqual(
            [item.title for item in response.context["latest_news"]],
            ["News 5", "News 4", "News 3", "News 2", "News 1", "News 0"],
        )
        self.assertEqual(
            [item.title for item in response.context["latest_updates"]],
            ["News 5", "News 4", "News 3", "News 2", "News 1", "News 0"],
        )

    def test_updates_page_merges_announcements_and_news_into_single_section(self):
        announcement = Announcement.objects.create(
            title="University advisory",
            content="Campus offices will be closed on Friday.",
            department=self.department,
        )
        news_item = News.objects.create(
            title="Science showcase opens",
            content="<p>The science showcase opens this week.</p>",
            department=self.department,
        )
        announcement_timestamp = timezone.now() - timedelta(days=2)
        news_timestamp = timezone.now() - timedelta(days=1)
        Announcement.objects.filter(pk=announcement.pk).update(date_posted=announcement_timestamp)
        News.objects.filter(pk=news_item.pk).update(date_posted=news_timestamp)
        announcement.refresh_from_db()
        news_item.refresh_from_db()

        response = self.client.get(reverse("core:updates"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Latest announcements and news")
        self.assertNotContains(response, "More news updates")
        self.assertNotContains(response, 'id="announcements"')
        self.assertNotContains(response, 'id="news"')
        self.assertContains(response, "Announcement")
        self.assertContains(response, "News")
        self.assertEqual(
            [item.title for item in response.context["latest_updates"][:2]],
            ["Science showcase opens", "University advisory"],
        )
        self.assertContains(
            response,
            reverse("core:update_detail", args=["news", news_item.pk]),
        )

    def test_homepage_featured_news_also_appears_on_updates_page(self):
        featured_news = News.objects.create(
            title="Homepage featured story",
            content="<p>This story is highlighted on the homepage.</p>",
            department=self.department,
        )

        home_response = self.client.get(reverse("core:home"))
        updates_response = self.client.get(reverse("core:updates"))

        self.assertEqual(home_response.status_code, 200)
        self.assertEqual(updates_response.status_code, 200)
        self.assertEqual(home_response.context["featured_news"][0].pk, featured_news.pk)
        self.assertEqual(updates_response.context["latest_updates"][0].pk, featured_news.pk)
        self.assertContains(updates_response, "Homepage featured story")

    def test_update_detail_page_displays_single_news_item_with_back_link(self):
        news_item = News.objects.create(
            title="Campus bulletin",
            content="<p>Complete update details for the bulletin.</p>",
            department=self.department,
        )

        response = self.client.get(reverse("core:update_detail", args=["news", news_item.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Campus bulletin")
        self.assertContains(response, "Complete update details for the bulletin.")
        self.assertContains(response, reverse("core:updates") + "#updates")
        self.assertContains(response, 'class="nav-link is-active"', html=False)

    def test_update_detail_page_displays_single_announcement_item(self):
        announcement = Announcement.objects.create(
            title="Advisory notice",
            content="<p>Announcement details shown on its own page.</p>",
            department=self.department,
        )

        response = self.client.get(reverse("core:update_detail", args=["announcement", announcement.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Advisory notice")
        self.assertContains(response, "Announcement details shown on its own page.")

    def test_event_detail_page_displays_single_event_with_back_link(self):
        event = Event.objects.create(
            title="Alumni Home Coming",
            description="<p>Full public event details appear on the dedicated page.</p>",
            department=self.department,
            event_date=timezone.now() + timedelta(days=5),
            location="NORSU Arena",
        )

        response = self.client.get(reverse("core:event_detail", args=[event.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alumni Home Coming")
        self.assertContains(response, "Full public event details appear on the dedicated page.")
        self.assertContains(response, reverse("core:updates") + "#events")
        self.assertContains(response, 'class="mission-vision-card update-detail-card"', html=False)
        self.assertContains(response, 'class="update-detail-chip"', html=False)

    def test_public_pages_hide_draft_updates_and_events(self):
        Announcement.objects.create(
            title="Published advisory",
            content="Visible announcement.",
            department=self.department,
        )
        Announcement.objects.create(
            title="Draft advisory",
            content="Hidden draft announcement.",
            department=self.department,
            publication_status=PublicationStatus.DRAFT,
        )
        Event.objects.create(
            title="Published event",
            description="Visible event details.",
            department=self.department,
            event_date=timezone.now() + timedelta(days=1),
            location="Gymnasium",
        )
        Event.objects.create(
            title="Draft event",
            description="Hidden draft event.",
            department=self.department,
            event_date=timezone.now() + timedelta(days=2),
            location="Library",
            publication_status=PublicationStatus.DRAFT,
        )

        updates_response = self.client.get(reverse("core:updates"))
        home_response = self.client.get(reverse("core:home"))

        self.assertContains(updates_response, "Published advisory")
        self.assertNotContains(updates_response, "Draft advisory")
        self.assertContains(updates_response, "Published event")
        self.assertNotContains(updates_response, "Draft event")
        self.assertNotContains(home_response, "Draft advisory")

    def test_homepage_keeps_institutional_sections_in_about_nav_only(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Mission text for the homepage.")
        self.assertNotContains(response, "Vision text for the homepage.")
        self.assertNotContains(response, "Strategic goals text for the homepage.")
        self.assertNotContains(response, "Quality policy text for the homepage.")
        self.assertNotContains(response, "SHINE")
        self.assertNotContains(response, 'href="#mission"')
        self.assertNotContains(response, 'id="mission"')
        self.assertNotContains(response, 'id="vision"')
        self.assertNotContains(response, 'id="core-values"')
        self.assertNotContains(response, 'id="strategic-goals"')
        self.assertNotContains(response, 'id="quality-policy"')
        self.assertContains(response, f'href="{reverse("core:about")}"')
        self.assertNotContains(response, "Institutional purpose")
        self.assertNotContains(response, "Long-term direction")
        self.assertContains(response, 'id="siteNavAboutDropdown"')
        self.assertContains(response, "About")
        self.assertContains(response, f'href="{reverse("core:about")}#history"')
        self.assertContains(response, f'href="{reverse("core:about")}#mission-vision"')
        self.assertNotContains(response, f'href="{reverse("core:mission")}"')
        self.assertNotContains(response, f'href="{reverse("core:vision")}"')
        self.assertContains(response, f'href="{reverse("core:about")}#strategic-goals"')
        self.assertContains(response, f'href="{reverse("core:about")}#core-values"')
        self.assertContains(response, f'href="{reverse("core:about")}#quality-policy"')

    def test_homepage_nav_links_norsu_calendar_to_about_page_section(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'<li><a class="dropdown-item" href="{reverse("core:about")}#calendar">NORSU Calendar</a></li>',
            html=False,
        )
        self.assertNotContains(
            response,
            f'<li class="nav-item site-nav-item"><a class="nav-link" href="{reverse("core:calendar")}">NORSU Calendar</a></li>',
            html=False,
        )
        self.assertNotContains(response, reverse("core:updates") + "#events")

    def test_homepage_links_latest_announcement_news_and_event(self):
        announcement = Announcement.objects.create(
            title="University advisory",
            content="Latest campus advisory for students.",
            department=self.department,
        )
        news_item = News.objects.create(
            title="Campus innovation story",
            content="<p>Innovation news appears on the homepage.</p>",
            department=self.department,
        )
        event = Event.objects.create(
            title="Student research forum",
            description="<p>Research forum details are linked on the homepage.</p>",
            department=self.department,
            event_date=timezone.now() + timedelta(days=4),
            location="Main Hall",
        )

        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Latest announcements and news")
        self.assertContains(response, "Upcoming and recent events")
        self.assertContains(response, announcement.title)
        self.assertContains(response, reverse("core:update_detail", args=["announcement", announcement.pk]))
        self.assertContains(response, news_item.title)
        self.assertContains(response, reverse("core:update_detail", args=["news", news_item.pk]))
        self.assertContains(response, event.title)
        self.assertContains(response, reverse("core:event_detail", args=[event.pk]))

    def test_homepage_contact_nav_points_to_standalone_contact_page(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{reverse("core:contact")}"')
        self.assertNotContains(response, 'href="#contact"')

    def test_about_page_displays_all_about_sections(self):
        response = self.client.get(reverse("core:about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "About NORSU")
        self.assertContains(response, 'id="history"')
        self.assertContains(response, 'id="mission-vision"')
        self.assertContains(response, 'id="strategic-goals"')
        self.assertContains(response, 'id="core-values"')
        self.assertContains(response, 'id="quality-policy"')
        self.assertContains(response, 'id="calendar"')
        self.assertContains(response, 'class="mission-vision-card h-100"', html=False)
        self.assertContains(response, "Mission and vision")
        self.assertNotContains(response, "Institutional purpose")
        self.assertNotContains(response, "Long-term direction")
        self.assertContains(response, "Mission text for the homepage.")
        self.assertContains(response, 'class="nav-link dropdown-toggle is-active"', html=False)
        self.assertContains(response, "Vision text for the homepage.")
        self.assertContains(response, "Strategic goals text for the homepage.")
        self.assertContains(response, "Core values text for the homepage.")
        self.assertContains(response, "Quality policy text for the homepage.")
        self.assertContains(response, "NORSU Calendar 2025-2026")

    def test_legacy_mission_and_vision_pages_redirect_to_combined_page(self):
        mission_response = self.client.get(reverse("core:mission"))
        vision_response = self.client.get(reverse("core:vision"))

        self.assertRedirects(mission_response, reverse("core:about") + "#mission-vision", fetch_redirect_response=False)
        self.assertRedirects(vision_response, reverse("core:about") + "#mission-vision", fetch_redirect_response=False)

    def test_legacy_about_section_pages_redirect_to_about_page_sections(self):
        history_response = self.client.get(reverse("core:history"))
        mission_vision_response = self.client.get(reverse("core:mission_vision"))
        strategic_goals_response = self.client.get(reverse("core:strategic_goals"))
        core_values_response = self.client.get(reverse("core:core_values"))
        quality_policy_response = self.client.get(reverse("core:quality_policy"))
        calendar_response = self.client.get(reverse("core:calendar"))

        self.assertRedirects(history_response, reverse("core:about") + "#history", fetch_redirect_response=False)
        self.assertRedirects(mission_vision_response, reverse("core:about") + "#mission-vision", fetch_redirect_response=False)
        self.assertRedirects(strategic_goals_response, reverse("core:about") + "#strategic-goals", fetch_redirect_response=False)
        self.assertRedirects(core_values_response, reverse("core:about") + "#core-values", fetch_redirect_response=False)
        self.assertRedirects(quality_policy_response, reverse("core:about") + "#quality-policy", fetch_redirect_response=False)
        self.assertRedirects(calendar_response, reverse("core:about") + "#calendar", fetch_redirect_response=False)

    def test_contact_page_displays_standalone_contact_content(self):
        response = self.client.get(reverse("core:contact"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contact NORSU")
        self.assertContains(response, "Bayawan City, Negros Oriental")
        self.assertContains(response, "norsu@email.com")
        self.assertContains(response, "+63 912 345 6789")
        self.assertContains(response, 'class="nav-link is-active"', html=False)

    def test_strategic_goals_page_displays_public_content(self):
        response = self.client.get(reverse("core:about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "University strategic goals")
        self.assertContains(response, "Strategic goals text for the homepage.")
        self.assertContains(response, 'class="nav-link dropdown-toggle is-active"', html=False)

    def test_strategic_goals_page_renders_structured_goal_cards_when_configured(self):
        self.school_info.strategic_goals = (
            "1. Strengthen instruction and curriculum relevance\n"
            "2. Expand responsive research and innovation\n"
            "3. Deepen community engagement and public service\n"
            "4. Advance student support and graduate readiness\n"
            "5. Reinforce accountable governance and stewardship\n"
            "6. Elevate partnerships and extension impact"
        )
        self.school_info.save(update_fields=["strategic_goals"])

        response = self.client.get(reverse("core:about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'class="shine-value-card core-values-page-value strategic-goal-page-value h-100 w-100"',
            html=False,
        )
        self.assertContains(
            response,
            'class="col-12 d-flex strategic-goal-page-column"',
            html=False,
        )
        self.assertContains(response, ">A<", html=False)
        self.assertContains(response, ">S<", html=False)
        self.assertContains(response, ">P<", html=False)
        self.assertContains(response, ">I<", html=False)
        self.assertContains(response, ">R<", html=False)
        self.assertContains(response, ">E<", html=False)
        self.assertContains(response, "Negros Oriental State University will:")
        self.assertContains(response, "Strengthen instruction and curriculum relevance")
        self.assertContains(response, "Expand responsive research and innovation")
        self.assertContains(response, "Deepen community engagement and public service")
        self.assertContains(response, "Advance student support and graduate readiness")
        self.assertContains(response, "Reinforce accountable governance and stewardship")
        self.assertContains(response, "Elevate partnerships and extension impact")

    def test_strategic_goals_page_renders_dash_separated_goal_content_as_cards(self):
        self.school_info.strategic_goals = (
            "- Strengthen instruction and curriculum relevance"
            " - Expand responsive research and innovation"
            " - Deepen community engagement and public service"
            " - Advance student support and graduate readiness"
            " - Reinforce accountable governance and stewardship"
            " - Elevate partnerships and extension impact"
        )
        self.school_info.save(update_fields=["strategic_goals"])

        response = self.client.get(reverse("core:about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Negros Oriental State University will:")
        self.assertContains(response, "Strengthen instruction and curriculum relevance")
        self.assertContains(response, "Expand responsive research and innovation")
        self.assertContains(response, "Deepen community engagement and public service")
        self.assertContains(response, "Advance student support and graduate readiness")
        self.assertContains(response, "Reinforce accountable governance and stewardship")
        self.assertContains(response, "Elevate partnerships and extension impact")
        self.assertContains(response, ">A<", html=False)
        self.assertContains(response, ">S<", html=False)
        self.assertContains(response, ">P<", html=False)
        self.assertContains(response, ">I<", html=False)
        self.assertContains(response, ">R<", html=False)
        self.assertContains(response, ">E<", html=False)
        self.assertContains(
            response,
            'class="shine-value-card core-values-page-value strategic-goal-page-value h-100 w-100"',
            html=False,
        )

    def test_core_values_page_displays_public_content(self):
        response = self.client.get(reverse("core:about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "University core values")
        self.assertContains(response, "Core values text for the homepage.")
        self.assertContains(response, 'class="nav-link dropdown-toggle is-active"', html=False)

    def test_core_values_page_renders_structured_shine_values_when_configured(self):
        self.school_info.core_values = "S - Spirituality H - Honesty I - Innovation N - Nurturance E - Excellence"
        self.school_info.save(update_fields=["core_values"])

        response = self.client.get(reverse("core:about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'class="row g-4 justify-content-center home-core-values-grid core-values-page-grid"',
            html=False,
        )
        self.assertContains(
            response,
            'class="col-sm-6 col-lg-4 col-xl d-flex"',
            html=False,
        )
        self.assertContains(response, "Spirituality")
        self.assertContains(response, "Honesty")
        self.assertContains(response, "Innovation")
        self.assertContains(response, "Nurturance")
        self.assertContains(response, "Excellence")

    def test_core_values_page_renders_line_separated_values_as_stacked_cards(self):
        self.school_info.core_values = "Spirituality\nHonesty\nInnovation\nNurturance\nExcellence"
        self.school_info.save(update_fields=["core_values"])

        response = self.client.get(reverse("core:about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'class="col-sm-6 col-lg-4 col-xl d-flex"',
            html=False,
        )
        self.assertContains(response, ">S<", html=False)
        self.assertContains(response, ">H<", html=False)
        self.assertContains(response, ">I<", html=False)
        self.assertContains(response, ">N<", html=False)
        self.assertContains(response, ">E<", html=False)
        self.assertContains(response, "Spirituality")
        self.assertContains(response, "Honesty")
        self.assertContains(response, "Innovation")
        self.assertContains(response, "Nurturance")
        self.assertContains(response, "Excellence")

    def test_quality_policy_page_displays_public_content(self):
        response = self.client.get(reverse("core:about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "University quality policy")
        self.assertContains(response, "Quality policy text for the homepage.")
        self.assertContains(response, 'class="nav-link dropdown-toggle is-active"', html=False)


    def test_homepage_features_departments_with_active_department_admins(self):
        featured_department = Department.objects.create(
            name="College of Engineering",
            code="COE",
            description="This description should stay off the homepage cards.",
            theme_color="#225588",
            is_active=True,
        )
        Department.objects.create(
            name="College of Hospitality",
            code="COH",
            description="Hospitality department.",
            theme_color="#225588",
            is_active=True,
        )
        User.objects.create_user(
            username="coe_admin",
            email="coe@example.com",
            password="testpass123",
            full_name="Engr. Jane Dean",
            role=RoleChoices.DEPARTMENT_ADMIN,
            department=featured_department,
        )

        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [department.code for department in response.context["featured_departments"]],
            ["COE"],
        )
        self.assertNotContains(response, "This description should stay off the homepage cards.")

    def test_homepage_and_updates_include_global_super_admin_posts(self):
        Announcement.objects.create(
            title="University-wide advisory",
            content="Classes are suspended for the foundation day celebration.",
        )
        global_news = News.objects.create(
            title="Global homepage story",
            content="<p>This news item should appear without a department.</p>",
        )

        home_response = self.client.get(reverse("core:home"))
        updates_response = self.client.get(reverse("core:updates"))

        self.assertEqual(home_response.status_code, 200)
        self.assertContains(home_response, "Global homepage story")
        self.assertContains(home_response, "University |")
        self.assertEqual(home_response.context["featured_news"][0].pk, global_news.pk)

        self.assertEqual(updates_response.status_code, 200)
        self.assertContains(updates_response, "University-wide advisory")
        self.assertContains(updates_response, "University |")

    def test_updates_include_global_super_admin_event(self):
        Event.objects.create(
            title="University Service Awards",
            description="Annual recognition ceremony for service awardees.",
            event_date=timezone.now() + timedelta(days=7),
            location="University Gymnasium",
        )

        response = self.client.get(reverse("core:updates"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "University Service Awards")
        self.assertContains(response, "University |")

    def test_updates_page_displays_multi_day_event_date_range(self):
        Event.objects.create(
            title="Research Congress",
            description="Three-day academic event.",
            event_date=timezone.datetime(2026, 4, 7, 9, 0, tzinfo=timezone.get_current_timezone()),
            end_date=timezone.datetime(2026, 4, 9, 17, 0, tzinfo=timezone.get_current_timezone()),
            location="University Convention Hall",
        )

        response = self.client.get(reverse("core:updates"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apr 07, 2026 | 9:00 AM - Apr 09, 2026 | 5:00 PM")


class PublicAlumniViewTests(TestCase):
    def setUp(self):
        self.department_a = Department.objects.create(
            name="College of Science",
            code="COS",
            description="Science programs and updates.",
            theme_color="#12345b",
            is_active=True,
        )
        self.department_b = Department.objects.create(
            name="College of Engineering",
            code="COE",
            description="Engineering programs and updates.",
            theme_color="#23456c",
            is_active=True,
        )
        SchoolInfo.objects.create(
            college_name="Negros Oriental State University",
            mission="Mission text for the homepage.",
            vision="Vision text for the homepage.",
            strategic_goals="Strategic goals text for the homepage.",
            core_values="Core values text for the homepage.",
            quality_policy="Quality policy text for the homepage.",
            history="History text.",
        )

    def create_alumnus(self, *, full_name, department, batch_year, is_public=True):
        return Alumni.objects.create(
            full_name=full_name,
            id_number=f"{batch_year}-{full_name[:3]}",
            batch_year=batch_year,
            course_program="BS Computer Science",
            department=department,
            email=f"{full_name.lower().replace(' ', '.')}@example.com",
            contact_number="09123456789",
            address="Bayawan City",
            employment_status="Employed",
            company_name="NORSU",
            job_title="Developer",
            is_public=is_public,
        )

    def test_alumni_page_hides_alumni_until_department_is_selected(self):
        self.create_alumnus(
            full_name="Alex Santos",
            department=self.department_a,
            batch_year=2024,
        )
        self.create_alumnus(
            full_name="Bea Reyes",
            department=self.department_a,
            batch_year=2023,
        )

        response = self.client.get(reverse("core:alumni"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["public_alumni"]), [])
        self.assertEqual(response.context["batch_options"], [])
        self.assertEqual(response.context["selected_batch"], "")
        self.assertContains(response, "Select a department to view alumni profiles.")
        self.assertNotContains(response, "Alex Santos")
        self.assertNotContains(response, "Bea Reyes")
        self.assertContains(response, 'id="alumni-batch-filter"', html=False)
        self.assertContains(response, "disabled")

    def test_alumni_page_filters_by_selected_batch(self):
        newer_alumnus = self.create_alumnus(
            full_name="Alex Santos",
            department=self.department_a,
            batch_year=2024,
        )
        self.create_alumnus(
            full_name="Bea Reyes",
            department=self.department_a,
            batch_year=2023,
        )

        response = self.client.get(
            reverse("core:alumni"),
            {"department": str(self.department_a.pk), "batch": "2024"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["public_alumni"]), [newer_alumnus])
        self.assertContains(response, "Filter by Batch")
        self.assertContains(response, "Alex Santos")
        self.assertNotContains(response, "Bea Reyes")
        self.assertEqual(response.context["selected_batch"], "2024")
        self.assertEqual(response.context["batch_options"], [2024, 2023])

    def test_alumni_page_combines_department_and_batch_filters(self):
        matching_alumnus = self.create_alumnus(
            full_name="Carla Gomez",
            department=self.department_a,
            batch_year=2024,
        )
        self.create_alumnus(
            full_name="Dino Cruz",
            department=self.department_a,
            batch_year=2023,
        )
        self.create_alumnus(
            full_name="Ella Tan",
            department=self.department_b,
            batch_year=2024,
        )
        self.create_alumnus(
            full_name="Hidden Profile",
            department=self.department_a,
            batch_year=2024,
            is_public=False,
        )

        response = self.client.get(
            reverse("core:alumni"),
            {"department": str(self.department_a.pk), "batch": "2024"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["public_alumni"]), [matching_alumnus])
        self.assertEqual(response.context["selected_department"], str(self.department_a.pk))
        self.assertEqual(response.context["selected_batch"], "2024")
        self.assertEqual(response.context["batch_options"], [2024, 2023])
        self.assertContains(response, "Carla Gomez")
        self.assertNotContains(response, "Dino Cruz")
        self.assertNotContains(response, "Ella Tan")
        self.assertNotContains(response, "Hidden Profile")

    def test_alumni_page_department_options_only_include_departments_with_public_alumni(self):
        department_without_public_alumni = Department.objects.create(
            name="College of Nursing",
            code="CON",
            description="Nursing programs and updates.",
            theme_color="#34567d",
            is_active=True,
        )
        self.create_alumnus(
            full_name="Ivan Lopez",
            department=self.department_a,
            batch_year=2022,
        )
        self.create_alumnus(
            full_name="Jessa Uy",
            department=department_without_public_alumni,
            batch_year=2022,
            is_public=False,
        )

        response = self.client.get(reverse("core:alumni"))

        self.assertEqual(response.status_code, 200)
        department_codes = [department.code for department in response.context["department_options"]]
        self.assertEqual(department_codes, ["COS"])
        self.assertContains(response, "College of Science (1)")
        self.assertNotContains(response, "College of Nursing")

    def test_alumni_page_shows_selected_department_label(self):
        self.create_alumnus(
            full_name="Karen Diaz",
            department=self.department_b,
            batch_year=2021,
        )

        response = self.client.get(
            reverse("core:alumni"),
            {"department": str(self.department_b.pk)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_department_name"], self.department_b.name)
        self.assertContains(response, "Showing alumni from")
        self.assertContains(response, self.department_b.name)


@override_settings(MEDIA_ROOT=str(TEST_MEDIA_ROOT))
class HistoryPageMediaTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_homepage_displays_uploaded_landing_background_image_and_intro_words(self):
        SchoolInfo.objects.create(
            college_name="Negros Oriental State University",
            mission="Mission text.",
            vision="Vision text.",
            history="History text.",
            landing_background_image=SimpleUploadedFile("landing.gif", TEST_GIF, content_type="image/gif"),
        )

        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="hero-section home-hero-section home-intro-hero"', html=False)
        self.assertContains(response, "school_info/landing/landing")
        self.assertContains(response, 'id="homeHeroWord"')
        self.assertContains(response, "OUR PRIDE")

    def test_about_page_displays_uploaded_calendar_images(self):
        school_info = SchoolInfo.objects.create(
            college_name="Negros Oriental State University",
            mission="Mission text.",
            vision="Vision text.",
            history="History text.",
        )
        first_image = CalendarImage.objects.create(
            school_info=school_info,
            image=SimpleUploadedFile("calendar-first.gif", TEST_GIF, content_type="image/gif"),
        )
        second_image = CalendarImage.objects.create(
            school_info=school_info,
            image=SimpleUploadedFile("calendar-second.gif", TEST_GIF, content_type="image/gif"),
        )

        response = self.client.get(reverse("core:about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NORSU Calendar")
        self.assertContains(response, first_image.image.url)
        self.assertContains(response, second_image.image.url)
        self.assertNotContains(response, ">Picture<", html=False)

    def test_about_page_uses_calendar_image_sort_order(self):
        school_info = SchoolInfo.objects.create(
            college_name="Negros Oriental State University",
            mission="Mission text.",
            vision="Vision text.",
            history="History text.",
        )
        first_image = CalendarImage.objects.create(
            school_info=school_info,
            image=SimpleUploadedFile("calendar-order-first.gif", TEST_GIF, content_type="image/gif"),
            sort_order=1,
        )
        second_image = CalendarImage.objects.create(
            school_info=school_info,
            image=SimpleUploadedFile("calendar-order-second.gif", TEST_GIF, content_type="image/gif"),
            sort_order=0,
        )

        response = self.client.get(reverse("core:about"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertLess(html.index(second_image.image.url), html.index(first_image.image.url))

    def test_updates_page_renders_uploaded_videos_for_updates_and_events(self):
        department = Department.objects.create(
            name="College of Media",
            code="COM",
            description="Media department.",
            theme_color="#12345b",
            is_active=True,
        )
        news_item = News.objects.create(
            title="Video campus update",
            content="<p>Update with uploaded video.</p>",
            department=department,
            video=build_test_video(name="updates-preview.mp4"),
        )
        event = Event.objects.create(
            title="Video campus event",
            description="<p>Event with uploaded video.</p>",
            department=department,
            event_date=timezone.now(),
            location="Main Hall",
            video=build_test_video(name="events-preview.mp4"),
        )

        response = self.client.get(reverse("core:updates"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="news-carousel-video"', html=False)
        self.assertContains(response, news_item.video.url)
        self.assertContains(response, event.video.url)

    def test_update_detail_page_displays_uploaded_video(self):
        department = Department.objects.create(
            name="College of Media Studies",
            code="CMS",
            description="Media studies department.",
            theme_color="#12345b",
            is_active=True,
        )
        news_item = News.objects.create(
            title="Video story",
            content="<p>Full update detail with video.</p>",
            department=department,
            video=build_test_video(name="detail-update.mp4"),
        )

        response = self.client.get(reverse("core:update_detail", args=["news", news_item.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="update-detail-video"', html=False)
        self.assertContains(response, news_item.video.url)

    def test_event_detail_page_displays_uploaded_video(self):
        department = Department.objects.create(
            name="College of Event Media",
            code="CEM",
            description="Event media department.",
            theme_color="#12345b",
            is_active=True,
        )
        event = Event.objects.create(
            title="Video event detail",
            description="<p>Full public event detail with video.</p>",
            department=department,
            event_date=timezone.now(),
            location="Arena",
            video=build_test_video(name="detail-event.mp4"),
        )

        response = self.client.get(reverse("core:event_detail", args=[event.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="update-detail-video"', html=False)
        self.assertContains(response, event.video.url)

    def test_about_page_displays_uploaded_history_image(self):
        SchoolInfo.objects.create(
            college_name="Negros Oriental State University",
            mission="Mission text.",
            vision="Vision text.",
            history="History text.",
            history_image=SimpleUploadedFile("history.gif", TEST_GIF, content_type="image/gif"),
        )

        response = self.client.get(reverse("core:about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="history-card-layout history-card-layout--with-media"')
        self.assertContains(response, 'class="history-card-image"')

    def test_about_page_uses_default_media_history_image_when_present(self):
        history_image_dir = TEST_MEDIA_ROOT / "content" / "images"
        history_image_dir.mkdir(parents=True, exist_ok=True)
        (history_image_dir / "history_pic.jpg").write_bytes(TEST_GIF)

        SchoolInfo.objects.create(
            college_name="Negros Oriental State University",
            mission="Mission text.",
            vision="Vision text.",
            history="History text.",
        )

        response = self.client.get(reverse("core:about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/media/content/images/history_pic.jpg')
        self.assertContains(response, 'class="history-card-image"')

    def test_about_page_history_collapses_single_line_breaks_into_normal_paragraphs(self):
        SchoolInfo.objects.create(
            college_name="Negros Oriental State University",
            mission="Mission text.",
            vision="Vision text.",
            history=(
                "July 5, 1946, a day after the\n"
                "historic signing of the Treaty of Manila\n"
                "between the United States of America.\n\n"
                "A second paragraph starts here."
            ),
        )

        response = self.client.get(reverse("core:about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "July 5, 1946, a day after the historic signing of the Treaty of Manila between the United States of America.",
        )
        self.assertContains(response, "<p>A second paragraph starts here.</p>", html=True)
