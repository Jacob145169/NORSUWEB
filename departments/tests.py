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
from academics.models import Instructor, Program, ProgramUniformImage
from content.models import Announcement, Event, News, PublicationStatus
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


def build_test_video(*, name="test.mp4"):
    return SimpleUploadedFile(name, b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41", content_type="video/mp4")


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
            theme_color_secondary="#2563eb",
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
        self.program = Program.objects.create(
            program_code="BSPSY",
            program_name="Bachelor of Science in Psychology",
            description="Psychology program description.",
            course_uniform_description="Use the official psychology uniform with the approved department patch during practicum and campus functions.",
            department=self.department,
        )
        self.program_uniform_front = ProgramUniformImage.objects.create(
            program=self.program,
            image=build_test_image(900, 1200, name="psychology-uniform-front.png"),
            sort_order=0,
        )
        self.program_uniform_back = ProgramUniformImage.objects.create(
            program=self.program,
            image=build_test_image(900, 1200, name="psychology-uniform-back.png"),
            sort_order=1,
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
        self.assertContains(response, self.program.program_name)
        self.assertContains(response, "Uniform Photos")
        self.assertContains(response, self.program.course_uniform_description)
        self.assertContains(response, "Dean and instructors")
        self.assertContains(response, "Assistant Dean")
        self.assertContains(response, "Dr. Maria Dean")
        self.assertContains(response, "Prof. Ana Cruz")
        self.assertContains(response, "Prof. Allan Cruz")
        self.assertContains(response, "/media/departments/leadership/dean")
        self.assertContains(response, "/media/departments/leadership/assistant")
        self.assertContains(response, self.program_uniform_front.image.url)
        self.assertContains(response, self.program_uniform_back.image.url)

    def test_department_detail_uses_department_banner_image(self):
        response = self.client.get(reverse("departments:detail", args=[self.department.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "department-themed-body")
        self.assertContains(response, "--department-theme: #12345b; --department-theme-secondary: #2563eb;")
        self.assertContains(response, "department-profile-banner--with-image")
        self.assertContains(response, self.department.banner_image.url)
        self.assertContains(response, "--department-theme-secondary: #2563eb;")

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

    def test_department_detail_event_cards_render_uploaded_video(self):
        event = Event.objects.create(
            title="Department video event",
            description="Visible event details.",
            department=self.department,
            event_date=timezone.now(),
            location="CAS Hall",
            video=build_test_video(name="department-event.mp4"),
        )

        response = self.client.get(reverse("departments:detail", args=[self.department.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="content-card-video"', html=False)
        self.assertContains(response, event.video.url)

    def test_department_detail_includes_links_to_full_updates_and_events(self):
        announcement = Announcement.objects.create(
            title="Published department notice",
            content="Visible to the public.",
            department=self.department,
        )
        news_item = News.objects.create(
            title="Department feature story",
            content="News story content for the department page.",
            department=self.department,
        )
        event = Event.objects.create(
            title="Published department event",
            description="Visible event details.",
            department=self.department,
            event_date=timezone.now(),
            location="CAS Hall",
        )

        response = self.client.get(reverse("departments:detail", args=[self.department.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("core:update_detail", args=["announcement", announcement.pk]))
        self.assertContains(response, reverse("core:update_detail", args=["news", news_item.pk]))
        self.assertContains(response, reverse("core:event_detail", args=[event.pk]))
        self.assertContains(response, "View Announcement")
        self.assertContains(response, "View News")
        self.assertContains(response, "View Event")


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
