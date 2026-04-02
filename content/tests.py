from django.test import SimpleTestCase, TestCase

from accounts.forms import NewsForm
from departments.models import Department

from .models import News
from .richtext import richtext_to_plaintext


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
