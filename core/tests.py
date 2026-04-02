from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from content.models import News
from departments.models import Department


class PublicNewsViewTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="College of Science",
            code="COS",
            description="Science programs and updates.",
            theme_color="#12345b",
            is_active=True,
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

    def test_updates_page_excludes_homepage_featured_news_items(self):
        self.create_news_batch()

        response = self.client.get(reverse("core:updates"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item.title for item in response.context["featured_news"]],
            ["News 5", "News 4", "News 3", "News 2"],
        )
        self.assertEqual(
            [item.title for item in response.context["latest_news"]],
            ["News 1", "News 0"],
        )
