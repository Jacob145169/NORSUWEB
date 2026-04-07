import shutil
from datetime import timedelta
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import RoleChoices, User
from content.models import Announcement, Event, News, PublicationStatus
from departments.models import Department, SchoolInfo


TEST_GIF = (
    b"GIF87a\x01\x00\x01\x00\x80\x00\x00"
    b"\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"
    b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)
TEST_MEDIA_ROOT = Path(__file__).resolve().parent.parent / ".test_media_core"


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
        self.assertContains(response, 'id="homepageNewsCarousel"')
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

    def test_homepage_shows_mission_vision_strategic_goals_core_values_and_quality_policy_without_nav_links(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mission text for the homepage.")
        self.assertContains(response, "Vision text for the homepage.")
        self.assertContains(response, "Strategic goals text for the homepage.")
        self.assertContains(response, "Core values text for the homepage.")
        self.assertContains(response, "Quality policy text for the homepage.")
        self.assertNotContains(response, "Institutional purpose")
        self.assertNotContains(response, "Long-term direction")
        self.assertNotContains(response, 'href="/mission/"')
        self.assertNotContains(response, 'href="/vision/"')

    def test_mission_page_hides_old_institutional_purpose_subheading(self):
        response = self.client.get(reverse("core:mission"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="mission-vision-card"', html=False)
        self.assertNotContains(response, "Institutional purpose")
        self.assertContains(response, "Mission text for the homepage.")

    def test_vision_page_hides_old_long_term_direction_subheading(self):
        response = self.client.get(reverse("core:vision"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="mission-vision-card"', html=False)
        self.assertNotContains(response, "Long-term direction")
        self.assertContains(response, "Vision text for the homepage.")

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


@override_settings(MEDIA_ROOT=str(TEST_MEDIA_ROOT))
class HistoryPageMediaTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_history_page_displays_uploaded_history_image(self):
        SchoolInfo.objects.create(
            college_name="Negros Oriental State University",
            mission="Mission text.",
            vision="Vision text.",
            history="History text.",
            history_image=SimpleUploadedFile("history.gif", TEST_GIF, content_type="image/gif"),
        )

        response = self.client.get(reverse("core:history"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="history-card-layout history-card-layout--with-media"')
        self.assertContains(response, 'class="history-card-image"')

    def test_history_page_uses_default_media_history_image_when_present(self):
        history_image_dir = TEST_MEDIA_ROOT / "content" / "images"
        history_image_dir.mkdir(parents=True, exist_ok=True)
        (history_image_dir / "history_pic.jpg").write_bytes(TEST_GIF)

        SchoolInfo.objects.create(
            college_name="Negros Oriental State University",
            mission="Mission text.",
            vision="Vision text.",
            history="History text.",
        )

        response = self.client.get(reverse("core:history"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/media/content/images/history_pic.jpg')
        self.assertContains(response, 'class="history-card-image"')

    def test_history_page_collapses_single_line_breaks_into_normal_paragraphs(self):
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

        response = self.client.get(reverse("core:history"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "July 5, 1946, a day after the historic signing of the Treaty of Manila between the United States of America.",
        )
        self.assertContains(response, "<p>A second paragraph starts here.</p>", html=True)
