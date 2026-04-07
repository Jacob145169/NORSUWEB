import io
import shutil
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from PIL import Image

from accounts.models import RoleChoices, User
from academics.models import Instructor, Program
from content.models import Announcement, Event, PublicationStatus
from departments.models import Department


TEST_GIF = (
    b"GIF87a\x01\x00\x01\x00\x80\x00\x00"
    b"\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"
    b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)
TEST_MEDIA_ROOT = Path(__file__).resolve().parent.parent / ".test_media_departments"


def build_test_image(width, height, *, name="test.png", color=(255, 255, 255)):
    buffer = io.BytesIO()
    image = Image.new("RGB", (width, height), color)
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=str(TEST_MEDIA_ROOT))
class DepartmentDetailViewTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.department = Department.objects.create(
            name="College of Arts and Sciences",
            code="CAS",
            description="Arts and sciences department.",
            mission="Deliver transformative arts and sciences education for lifelong learners.",
            vision="To be a leading arts and sciences department shaping ethical innovators.",
            banner_image=build_test_image(1600, 900, name="cas-banner.png"),
            dean_name="Dr. Maria Dean",
            assistant_dean_name="Prof. Ana Cruz",
            dean_photo=SimpleUploadedFile("dean.gif", TEST_GIF, content_type="image/gif"),
            assistant_dean_photo=SimpleUploadedFile("assistant.gif", TEST_GIF, content_type="image/gif"),
            theme_color="#12345b",
            is_active=True,
        )
        self.dean = User.objects.create_user(
            username="cas_admin",
            email="cas@example.com",
            password="testpass123",
            full_name="Dr. Maria Dean",
            role=RoleChoices.DEPARTMENT_ADMIN,
            department=self.department,
        )
        self.instructor = Instructor.objects.create(
            full_name="Prof. Allan Cruz",
            department=self.department,
        )
    def test_department_detail_shows_assigned_dean_and_instructors(self):
        response = self.client.get(reverse("departments:detail", args=[self.department.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dean"], self.dean)
        self.assertEqual(response.context["dean_name"], "Dr. Maria Dean")
        self.assertEqual(response.context["assistant_dean_name"], "Prof. Ana Cruz")
        self.assertContains(response, "Mission")
        self.assertContains(response, "Vision")
        self.assertContains(response, self.department.mission)
        self.assertContains(response, self.department.vision)
        self.assertContains(response, "Dean and instructors")
        self.assertContains(response, "Assistant Dean")
        self.assertContains(response, "Dr. Maria Dean")
        self.assertContains(response, "Prof. Ana Cruz")
        self.assertContains(response, "Prof. Allan Cruz")
        self.assertContains(response, "/media/departments/leadership/dean")
        self.assertContains(response, "/media/departments/leadership/assistant")

    def test_department_detail_uses_department_banner_image(self):
        response = self.client.get(reverse("departments:detail", args=[self.department.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "department-profile-banner--with-image")
        self.assertContains(response, self.department.banner_image.url)

    def test_department_detail_program_cards_do_not_repeat_code_and_show_full_description(self):
        Program.objects.create(
            program_code="BSIT AUTOMOTIVE",
            program_name="BSIT AUTOMOTIVE - Bachelor of Industrial Technology Major in Automotive",
            description="This is the complete department program description without truncation.",
            department=self.department,
        )

        response = self.client.get(reverse("departments:detail", args=[self.department.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "BSIT AUTOMOTIVE")
        self.assertContains(response, "Bachelor of Industrial Technology Major in Automotive")
        self.assertNotContains(response, "BSIT AUTOMOTIVE - Bachelor of Industrial Technology Major in Automotive")
        self.assertContains(response, "This is the complete department program description without truncation.")

    def test_department_detail_hides_draft_updates_and_events(self):
        Announcement.objects.create(
            title="Published department notice",
            content="Visible to the public.",
            department=self.department,
        )
        Announcement.objects.create(
            title="Draft department notice",
            content="Should stay hidden.",
            department=self.department,
            publication_status=PublicationStatus.DRAFT,
        )
        Event.objects.create(
            title="Published department event",
            description="Visible event details.",
            department=self.department,
            event_date=timezone.now(),
            location="CAS Hall",
        )
        Event.objects.create(
            title="Draft department event",
            description="Should stay hidden.",
            department=self.department,
            event_date=timezone.now(),
            location="CAS Hall",
            publication_status=PublicationStatus.DRAFT,
        )

        response = self.client.get(reverse("departments:detail", args=[self.department.slug]))

        self.assertContains(response, "Published department notice")
        self.assertNotContains(response, "Draft department notice")
        self.assertContains(response, "Published department event")
        self.assertNotContains(response, "Draft department event")


class DepartmentListViewTests(TestCase):
    def test_department_list_hides_description_from_cards(self):
        department = Department.objects.create(
            name="College of Business Administration",
            code="CBA",
            description="This description should only appear on the department detail page.",
            theme_color="#12345b",
            is_active=True,
        )

        response = self.client.get(reverse("departments:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, department.name)
        self.assertContains(response, "View Department")
        self.assertNotContains(response, department.description)
