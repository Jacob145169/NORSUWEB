from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from accounts.forms import AnnouncementForm, EventForm, NewsForm, UpdateCreateForm
from departments.models import Department

from .models import Announcement, Event, News
from .richtext import richtext_to_plaintext


class AnnouncementRichTextTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="College of Technology",
            code="COT",
            description="Technology and applied systems.",
            theme_color="#12345b",
            is_active=True,
        )

    def test_announcement_content_is_sanitized_on_save(self):
        announcement = Announcement.objects.create(
            title="Formatted Announcement",
            department=self.department,
            content=(
                '<p style="text-align:center;color:#123456;font-size:18px;font-family:Georgia;">'
                '<strong>Headline</strong>'
                '<script>alert("x")</script>'
                '<a href="javascript:alert(1)">Unsafe</a>'
                '<a href="https://example.com" target="_blank">Safe Link</a>'
                "</p>"
            ),
        )

        self.assertIn("<strong>Headline</strong>", announcement.content)
        self.assertIn("text-align: center", announcement.content)
        self.assertIn("color: #123456", announcement.content)
        self.assertIn("font-size: 18px", announcement.content)
        self.assertIn("font-family: Georgia", announcement.content)
        self.assertIn('href="https://example.com"', announcement.content)
        self.assertIn('rel="noopener noreferrer"', announcement.content)
        self.assertNotIn("<script", announcement.content)
        self.assertNotIn("javascript:", announcement.content)


class NewsRichTextTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="College of Technology",
            code="COT",
            description="Technology and applied systems.",
            theme_color="#12345b",
            is_active=True,
        )

    def test_news_content_is_sanitized_on_save(self):
        news = News.objects.create(
            title="Formatted Story",
            department=self.department,
            content=(
                '<p style="text-align:center;color:#123456;font-size:18px;font-family:Georgia;">'
                '<strong>Headline</strong>'
                '<script>alert("x")</script>'
                '<a href="javascript:alert(1)">Unsafe</a>'
                '<a href="https://example.com" target="_blank">Safe Link</a>'
                "</p>"
            ),
        )

        self.assertIn("<strong>Headline</strong>", news.content)
        self.assertIn("text-align: center", news.content)
        self.assertIn("color: #123456", news.content)
        self.assertIn("font-size: 18px", news.content)
        self.assertIn("font-family: Georgia", news.content)
        self.assertIn('href="https://example.com"', news.content)
        self.assertIn('rel="noopener noreferrer"', news.content)
        self.assertNotIn("<script", news.content)
        self.assertNotIn("javascript:", news.content)


class EventRichTextTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="College of Technology",
            code="COT",
            description="Technology and applied systems.",
            theme_color="#12345b",
            is_active=True,
        )

    def test_event_description_is_sanitized_on_save(self):
        event = Event.objects.create(
            title="Formatted Event",
            department=self.department,
            location="Auditorium",
            event_date=timezone.now(),
            description=(
                '<p style="text-align:center;color:#123456;font-size:18px;font-family:Georgia;">'
                '<strong>Event Details</strong>'
                '<script>alert("x")</script>'
                '<a href="javascript:alert(1)">Unsafe</a>'
                '<a href="https://example.com" target="_blank">Safe Link</a>'
                "</p>"
            ),
        )

        self.assertIn("<strong>Event Details</strong>", event.description)
        self.assertIn("text-align: center", event.description)
        self.assertIn("color: #123456", event.description)
        self.assertIn("font-size: 18px", event.description)
        self.assertIn("font-family: Georgia", event.description)
        self.assertIn('href="https://example.com"', event.description)
        self.assertIn('rel="noopener noreferrer"', event.description)
        self.assertNotIn("<script", event.description)
        self.assertNotIn("javascript:", event.description)

    def test_event_schedule_label_uses_date_range_for_multi_day_events(self):
        event = Event.objects.create(
            title="Founders Week",
            department=self.department,
            location="Campus Grounds",
            event_date=timezone.datetime(2026, 4, 7, 9, 0, tzinfo=timezone.get_current_timezone()),
            end_date=timezone.datetime(2026, 4, 9, 17, 0, tzinfo=timezone.get_current_timezone()),
            description="Three-day public event.",
        )

        self.assertEqual(
            event.schedule_label,
            "Apr 07, 2026 | 9:00 AM - Apr 09, 2026 | 5:00 PM",
        )


class NewsRichTextUtilityTests(SimpleTestCase):
    def test_plaintext_summary_collapses_rich_content(self):
        self.assertEqual(
            richtext_to_plaintext("<p><strong>First</strong></p><ul><li>Second</li></ul>"),
            "First Second",
        )

    def test_news_form_uses_tinymce_media(self):
        form = NewsForm()
        rendered_media = "".join(form.media.render_js())

        self.assertEqual(form.fields["content"].widget.attrs["data-richtext-editor"], "tinymce")
        self.assertIn("/static/vendor/tinymce/tinymce.min.js", rendered_media)

    def test_announcement_form_uses_tinymce_media(self):
        form = AnnouncementForm()
        rendered_media = "".join(form.media.render_js())

        self.assertEqual(form.fields["content"].widget.attrs["data-richtext-editor"], "tinymce")
        self.assertIn("/static/vendor/tinymce/tinymce.min.js", rendered_media)
        self.assertIn("video", form.fields)
        self.assertFalse(form.fields["video"].required)

    def test_event_form_uses_tinymce_media(self):
        form = EventForm()
        rendered_media = "".join(form.media.render_js())

        self.assertEqual(form.fields["description"].widget.attrs["data-richtext-editor"], "tinymce")
        self.assertIn("/static/vendor/tinymce/tinymce.min.js", rendered_media)
        self.assertIn("video", form.fields)
        self.assertFalse(form.fields["video"].required)

    def test_event_form_exposes_optional_end_date_field(self):
        form = EventForm()

        self.assertIn("end_date", form.fields)
        self.assertFalse(form.fields["end_date"].required)

    def test_news_form_exposes_optional_video_field(self):
        form = NewsForm()

        self.assertIn("video", form.fields)
        self.assertFalse(form.fields["video"].required)

    def test_shared_update_create_form_exposes_optional_video_field(self):
        form = UpdateCreateForm()

        self.assertIn("video", form.fields)
        self.assertFalse(form.fields["video"].required)
