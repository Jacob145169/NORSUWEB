import io
import shutil
from zipfile import ZIP_DEFLATED, ZipFile
from pathlib import Path
from xml.sax.saxutils import escape

from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from PIL import Image

from .forms import DepartmentForm
from alumni.models import Alumni
from content.models import Announcement, Event, News, PublicationStatus
from .models import RoleChoices, User
from academics.models import Program
from departments.models import Department, SchoolInfo


TEST_GIF = (
    b"GIF87a\x01\x00\x01\x00\x80\x00\x00"
    b"\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"
    b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)
TEST_MEDIA_ROOT = Path(__file__).resolve().parent.parent / ".test_media_accounts"


def build_test_image(width, height, *, name="test.png", color=(255, 255, 255)):
    buffer = io.BytesIO()
    image = Image.new("RGB", (width, height), color)
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def build_test_xlsx(rows, *, name="alumni-import.xlsx"):
    def column_letter(index):
        result = ""
        current = index + 1
        while current:
            current, remainder = divmod(current - 1, 26)
            result = chr(65 + remainder) + result
        return result

    worksheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row):
            if value in (None, ""):
                continue
            cell_reference = f"{column_letter(column_index)}{row_index}"
            cells.append(
                f'<c r="{cell_reference}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'
            )
        worksheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    workbook_buffer = io.BytesIO()
    with ZipFile(workbook_buffer, "w", ZIP_DEFLATED) as workbook:
        workbook.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        )
        workbook.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        workbook.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Sheet1" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>""",
        )
        workbook.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        workbook.writestr(
            "xl/worksheets/sheet1.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    {''.join(worksheet_rows)}
  </sheetData>
</worksheet>""",
        )

    workbook_buffer.seek(0)
    return SimpleUploadedFile(
        name,
        workbook_buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@override_settings(MEDIA_ROOT=str(TEST_MEDIA_ROOT))
class DepartmentLeadershipUpdateViewTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.department = Department.objects.create(
            name="College of Teacher Education",
            code="CTED",
            description="Teacher education department.",
            theme_color="#12345b",
            is_active=True,
        )
        self.department_admin = User.objects.create_user(
            username="cted_admin",
            email="cted@example.com",
            password="testpass123",
            full_name="Dean Admin",
            role=RoleChoices.DEPARTMENT_ADMIN,
            department=self.department,
        )

    def test_department_admin_can_update_dean_and_assistant_dean(self):
        self.client.force_login(self.department_admin)

        response = self.client.post(
            reverse("accounts:department_leadership_update"),
            {
                "mission": "Prepare future educators through practical and values-based instruction.",
                "vision": "To become a leading teacher education department in the region.",
                "dean_name": "Dr. Leonora Santos",
                "dean_photo": SimpleUploadedFile("dean.gif", TEST_GIF, content_type="image/gif"),
                "assistant_dean_name": "Prof. Miguel Ramos",
                "assistant_dean_photo": SimpleUploadedFile("assistant.gif", TEST_GIF, content_type="image/gif"),
                "banner_image": build_test_image(1200, 800, name="banner.png"),
            },
        )

        self.assertRedirects(response, reverse("accounts:department_admin_dashboard"))
        self.department.refresh_from_db()
        self.assertEqual(
            self.department.mission,
            "Prepare future educators through practical and values-based instruction.",
        )
        self.assertEqual(
            self.department.vision,
            "To become a leading teacher education department in the region.",
        )
        self.assertEqual(self.department.dean_name, "Dr. Leonora Santos")
        self.assertEqual(self.department.assistant_dean_name, "Prof. Miguel Ramos")
        self.assertTrue(bool(self.department.dean_photo))
        self.assertTrue(bool(self.department.assistant_dean_photo))
        self.assertTrue(bool(self.department.banner_image))

    def test_department_profile_form_shows_mission_and_vision_fields(self):
        self.client.force_login(self.department_admin)

        response = self.client.get(reverse("accounts:department_leadership_update"))

        self.assertContains(response, "<label for=\"id_mission\" class=\"form-label\">Department Mission</label>", html=False)
        self.assertContains(response, "<label for=\"id_vision\" class=\"form-label\">Department Vision</label>", html=False)

    def test_super_admin_department_form_hides_banner_field(self):
        self.client.force_login(User.objects.create_user(
            username="super_admin_form",
            email="superform@example.com",
            password="testpass123",
            full_name="Super Admin Form",
            role=RoleChoices.SUPER_ADMIN,
        ))

        response = self.client.get(reverse("accounts:department_create"))

        self.assertNotContains(response, "<label for=\"id_banner_image\" class=\"form-label\">Department Banner Background</label>", html=False)


class DepartmentAdminDashboardViewTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="College of Arts and Sciences",
            code="CAS",
            description="Arts and sciences department.",
            theme_color="#12345b",
            is_active=True,
        )
        self.department_admin = User.objects.create_user(
            username="cas_admin",
            email="cas@example.com",
            password="testpass123",
            full_name="CAS Admin",
            role=RoleChoices.DEPARTMENT_ADMIN,
            department=self.department,
        )

    def test_dashboard_merges_announcements_and_news_into_updates_section(self):
        Announcement.objects.create(
            title="Enrollment advisory",
            content="Enrollment is open for all CAS students.",
            department=self.department,
            posted_by=self.department_admin,
        )
        News.objects.create(
            title="CAS research wins award",
            content="<p>The department received a major research award.</p>",
            department=self.department,
            posted_by=self.department_admin,
        )

        self.client.force_login(self.department_admin)
        response = self.client.get(reverse("accounts:department_admin_dashboard"))

        self.assertContains(response, f'href="{reverse("accounts:update_list")}"')
        self.assertContains(response, f'href="{reverse("accounts:program_list")}"')
        self.assertContains(response, f'href="{reverse("accounts:instructor_list")}"')
        self.assertContains(response, f'href="{reverse("accounts:event_list")}"')
        self.assertContains(response, f'href="{reverse("accounts:alumni_list")}"')
        self.assertContains(response, "Recent Activity")
        self.assertContains(response, "Latest posts")
        self.assertContains(response, "Enrollment advisory")
        self.assertContains(response, "CAS research wins award")


class SchoolInfoUpdateViewTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            username="super_admin_school_info",
            email="schoolinfo@example.com",
            password="testpass123",
            full_name="Super Admin School Info",
            role=RoleChoices.SUPER_ADMIN,
        )

    def test_super_admin_can_update_strategic_goals_and_core_values(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(
            reverse("accounts:school_info_update"),
            {
                "college_name": "Negros Oriental State University",
                "mission": "Mission text",
                "vision": "Vision text",
                "strategic_goals": "Strategic Goals text",
                "core_values": "Core Values text",
                "quality_policy": "Quality Policy text",
                "history": "History text",
            },
        )

        self.assertRedirects(response, reverse("accounts:super_admin_dashboard"))
        school_info = SchoolInfo.get_solo()
        self.assertEqual(school_info.strategic_goals, "Strategic Goals text")
        self.assertEqual(school_info.core_values, "Core Values text")
        self.assertEqual(school_info.quality_policy, "Quality Policy text")

    def test_school_info_form_shows_strategic_goals_core_values_and_quality_policy_fields(self):
        self.client.force_login(self.super_admin)

        response = self.client.get(reverse("accounts:school_info_update"))

        self.assertContains(response, "<label for=\"id_strategic_goals\" class=\"form-label\">Strategic Goals</label>", html=False)
        self.assertContains(response, "<label for=\"id_core_values\" class=\"form-label\">Core Values</label>", html=False)
        self.assertContains(response, "<label for=\"id_quality_policy\" class=\"form-label\">Quality Policy</label>", html=False)


class DepartmentFormTests(TestCase):
    def test_accepts_department_banner_image_without_aspect_ratio_restriction(self):
        form = DepartmentForm(
            data={
                "name": "College of Industrial Technology",
                "code": "CIT",
                "description": "Industrial technology department.",
                "dean_name": "",
                "assistant_dean_name": "",
                "theme_color": "#12345b",
            },
            files={"banner_image": build_test_image(1200, 800, name="department-banner-invalid.png")},
        )

        self.assertTrue(form.is_valid(), form.errors)


class UpdateManagementViewTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="College of Engineering",
            code="COE",
            description="Engineering department.",
            theme_color="#0f4c81",
            is_active=True,
        )
        self.other_department = Department.objects.create(
            name="College of Business",
            code="CBA",
            description="Business department.",
            theme_color="#22543d",
            is_active=True,
        )
        self.department_admin = User.objects.create_user(
            username="coe_admin",
            email="coe@example.com",
            password="testpass123",
            full_name="COE Admin",
            role=RoleChoices.DEPARTMENT_ADMIN,
            department=self.department,
        )
        self.super_admin = User.objects.create_user(
            username="super_admin",
            email="super@example.com",
            password="testpass123",
            full_name="Super Admin",
            role=RoleChoices.SUPER_ADMIN,
        )

    def test_updates_list_merges_announcements_and_news_for_department_admin(self):
        Announcement.objects.create(
            title="Board exam briefing",
            content="Engineering students are required to attend the board exam briefing.",
            department=self.department,
            posted_by=self.department_admin,
        )
        News.objects.create(
            title="Engineering team wins hackathon",
            content="<p>The engineering team won the regional hackathon finals.</p>",
            department=self.department,
            posted_by=self.department_admin,
        )
        Announcement.objects.create(
            title="Other department notice",
            content="This should not be visible to COE.",
            department=self.other_department,
        )

        self.client.force_login(self.department_admin)
        response = self.client.get(reverse("accounts:update_list"))

        self.assertContains(response, "Department Update Management")
        self.assertContains(response, "Board exam briefing")
        self.assertContains(response, "Engineering team wins hackathon")
        self.assertNotContains(response, "Other department notice")
        self.assertContains(response, "Programs")
        self.assertContains(response, "Add Update")
        self.assertNotContains(response, "Manage Announcements")
        self.assertNotContains(response, "Manage News")
        self.assertNotContains(response, "Add Announcement")
        self.assertNotContains(response, "Add News")

    def test_legacy_announcement_and_news_routes_redirect_to_updates(self):
        self.client.force_login(self.department_admin)

        announcement_response = self.client.get(reverse("accounts:announcement_list"))
        news_response = self.client.get(reverse("accounts:news_list"))

        self.assertRedirects(announcement_response, reverse("accounts:update_list"))
        self.assertRedirects(news_response, reverse("accounts:update_list"))

    def test_super_admin_can_create_announcement_without_department(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(
            reverse("accounts:update_create"),
            {
                "content_type": "announcement",
                "title": "University enrollment advisory",
                "content": "Enrollment opens next week for all students.",
            },
        )

        self.assertRedirects(response, reverse("accounts:update_list"))
        announcement = Announcement.objects.get(title="University enrollment advisory")
        self.assertIsNone(announcement.department)
        self.assertEqual(announcement.posted_by, self.super_admin)

    def test_super_admin_create_form_hides_department_field(self):
        self.client.force_login(self.super_admin)

        response = self.client.get(reverse("accounts:update_create"))

        self.assertNotContains(response, "<label for=\"id_department\" class=\"form-label\">Department</label>", html=False)
        self.assertNotContains(response, "<label for=\"id_content_type\" class=\"form-label\">Type</label>", html=False)

    def test_shared_update_create_defaults_to_news_when_type_is_hidden(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(
            reverse("accounts:update_create"),
            {
                "title": "General campus update",
                "content": "This should be created through the default update flow.",
            },
        )

        self.assertRedirects(response, reverse("accounts:update_list"))
        self.assertTrue(News.objects.filter(title="General campus update").exists())

    def test_super_admin_can_create_event_without_department(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(
            reverse("accounts:event_create"),
            {
                "title": "University Recognition Day",
                "description": "Recognition rites for outstanding students.",
                "event_date": "2026-04-20T09:00",
                "location": "Main Auditorium",
            },
        )

        self.assertRedirects(response, reverse("accounts:event_list"))
        event = Event.objects.get(title="University Recognition Day")
        self.assertIsNone(event.department)
        self.assertEqual(event.posted_by, self.super_admin)

    def test_super_admin_can_create_multi_day_event(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(
            reverse("accounts:event_create"),
            {
                "title": "University Week",
                "description": "Three-day campus celebration.",
                "event_date": "2026-04-20T09:00",
                "end_date": "2026-04-22T17:00",
                "location": "Main Campus",
            },
        )

        self.assertRedirects(response, reverse("accounts:event_list"))
        event = Event.objects.get(title="University Week")
        self.assertEqual(event.schedule_label, "Apr 20, 2026 | 9:00 AM - Apr 22, 2026 | 5:00 PM")

    def test_super_admin_event_form_hides_department_field(self):
        self.client.force_login(self.super_admin)

        response = self.client.get(reverse("accounts:event_create"))

        self.assertNotContains(response, "<label for=\"id_department\" class=\"form-label\">Department</label>", html=False)
        self.assertContains(response, "<label for=\"id_end_date\" class=\"form-label\">End Date</label>", html=False)

    def test_legacy_update_create_routes_redirect_to_shared_create_form(self):
        self.client.force_login(self.department_admin)

        announcement_response = self.client.get(reverse("accounts:announcement_create"))
        news_response = self.client.get(reverse("accounts:news_create"))

        self.assertRedirects(announcement_response, f"{reverse('accounts:update_create')}?type=announcement")
        self.assertRedirects(news_response, f"{reverse('accounts:update_create')}?type=news")

    def test_shared_update_create_can_save_draft_and_continue_editing(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(
            reverse("accounts:update_create"),
            {
                "title": "Draft campus update",
                "content": "Draft content for later publishing.",
                "save_action": "draft",
            },
        )

        draft_news = News.objects.get(title="Draft campus update")
        self.assertRedirects(response, reverse("accounts:news_update", args=[draft_news.pk]))
        self.assertEqual(draft_news.publication_status, PublicationStatus.DRAFT)

        list_response = self.client.get(reverse("accounts:update_list"))
        self.assertContains(list_response, "Draft campus update")
        self.assertContains(list_response, "Draft")

    def test_event_create_can_save_draft_and_continue_editing(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(
            reverse("accounts:event_create"),
            {
                "title": "Draft Recognition Day",
                "description": "Draft recognition rites.",
                "event_date": "2026-04-20T09:00",
                "location": "Main Auditorium",
                "save_action": "draft",
            },
        )

        draft_event = Event.objects.get(title="Draft Recognition Day")
        self.assertRedirects(response, reverse("accounts:event_update", args=[draft_event.pk]))
        self.assertEqual(draft_event.publication_status, PublicationStatus.DRAFT)

    def test_publishing_existing_draft_makes_update_public(self):
        self.client.force_login(self.super_admin)
        draft_news = News.objects.create(
            title="Existing draft news",
            content="Draft body",
            posted_by=self.super_admin,
            publication_status=PublicationStatus.DRAFT,
        )

        response = self.client.post(
            reverse("accounts:news_update", args=[draft_news.pk]),
            {
                "title": "Existing draft news",
                "content": "Published body",
                "save_action": "publish",
            },
        )

        self.assertRedirects(response, reverse("accounts:update_list"))
        draft_news.refresh_from_db()
        self.assertEqual(draft_news.publication_status, PublicationStatus.PUBLISHED)


class AlumniImportTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="College of Industrial Technology",
            code="CIT",
            description="Industrial technology department.",
            theme_color="#12345b",
            is_active=True,
        )
        self.department_admin = User.objects.create_user(
            username="cit_admin_import",
            email="cit-import@example.com",
            password="testpass123",
            full_name="CIT Admin",
            role=RoleChoices.DEPARTMENT_ADMIN,
            department=self.department,
        )
        Program.objects.create(
            department=self.department,
            program_code="BSCT",
            program_name="Bachelor of Science in Computer Technology",
            description="Computer technology program.",
        )

    def test_department_admin_can_import_alumni_from_excel(self):
        self.client.force_login(self.department_admin)
        excel_file = build_test_xlsx(
            [
                [
                    "last_name",
                    "first_name",
                    "middle_initial",
                    "id_number",
                    "batch_year",
                    "course_program",
                    "email",
                    "contact_number",
                    "address",
                    "employment_status",
                    "company_name",
                    "job_title",
                    "is_public",
                ],
                [
                    "Tawagon",
                    "Mark Erol",
                    "L",
                    "123456789",
                    "2026",
                    "BSCT",
                    "mark@example.com",
                    "09123456789",
                    "Dumaguete City",
                    "Employed",
                    "Sample Company",
                    "Developer",
                    "yes",
                ],
            ]
        )

        response = self.client.post(
            reverse("accounts:alumni_create"),
            {"import_submit": "1", "excel_file": excel_file},
        )

        self.assertRedirects(response, reverse("accounts:alumni_list"))
        alumnus = Alumni.objects.get(id_number="123456789", department=self.department)
        self.assertEqual(alumnus.full_name, "Tawagon, Mark Erol L.")
        self.assertEqual(alumnus.course_program, "BSCT - Bachelor of Science in Computer Technology")
        self.assertTrue(alumnus.is_public)

    def test_import_form_rejects_invalid_excel_rows(self):
        self.client.force_login(self.department_admin)
        excel_file = build_test_xlsx(
            [
                [
                    "last_name",
                    "first_name",
                    "id_number",
                    "batch_year",
                    "course_program",
                    "email",
                    "contact_number",
                    "address",
                ],
                [
                    "Tawagon",
                    "Mark Erol",
                    "12345",
                    "2026",
                    "BSCT",
                    "mark@example.com",
                    "09123456789",
                    "Dumaguete City",
                ],
            ]
        )

        response = self.client.post(
            reverse("accounts:alumni_create"),
            {"import_submit": "1", "excel_file": excel_file},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Row 2: ID number must be exactly 9 numbers.")
        self.assertFalse(Alumni.objects.filter(department=self.department).exists())


@override_settings(MEDIA_ROOT=str(TEST_MEDIA_ROOT))
class AlumniExportPdfTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.department = Department.objects.create(
            name="College of Industrial Technology",
            code="CIT",
            description="Industrial technology department.",
            theme_color="#12345b",
            logo=build_test_image(300, 300, name="department-logo.png", color=(20, 80, 140)),
            is_active=True,
        )
        self.department_admin = User.objects.create_user(
            username="cit_admin_export",
            email="cit-export@example.com",
            password="testpass123",
            full_name="CIT Export Admin",
            role=RoleChoices.DEPARTMENT_ADMIN,
            department=self.department,
        )
        Alumni.objects.create(
            department=self.department,
            full_name="Tawagon, Mark Erol V.",
            id_number="202200703",
            batch_year=2026,
            course_program="BSIT COMP TECH - Bachelor of Industrial Technology Major in Computer Technology",
            email="erol@gmail.com",
            contact_number="09486154561",
            address="Dumaguete City",
        )
        Alumni.objects.create(
            department=self.department,
            full_name="Cordova, April S.",
            id_number="202200800",
            batch_year=2026,
            course_program="BSIT AUTOMOTIVE - Bachelor of Industrial Technology Major in Automotive",
            email="april@gmail.com",
            contact_number="9000000001",
            address="Dumaguete City",
        )

    def test_department_admin_can_export_filtered_alumni_pdf(self):
        self.client.force_login(self.department_admin)

        response = self.client.get(
            reverse("accounts:alumni_export_pdf"),
            {"q": "Mark"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF-1.4"))
        self.assertIn(b"/Subtype /Image", response.content)
        self.assertIn(b"/ExtGState", response.content)
        self.assertIn(b"/ca 0.08", response.content)

    def test_export_without_filters_uses_department_code_and_full_course_name(self):
        self.client.force_login(self.department_admin)

        response = self.client.get(reverse("accounts:alumni_export_pdf"))

        pdf_text = response.content.decode("latin-1", errors="ignore")
        self.assertIn("Department: CIT DEPARTMENT", pdf_text)
        self.assertIn("Bachelor of Industrial Technology Major in Computer Technology", pdf_text)
        self.assertIn("Bachelor of Industrial Technology Major in Automotive", pdf_text)
        self.assertNotIn("Filters:", pdf_text)
        self.assertNotIn("Course: BSIT COMP TECH -", pdf_text)
        self.assertNotIn("Course: Bachelor of Industrial Technology Major in Automotive", pdf_text)

        automotive_index = pdf_text.index("Bachelor of Industrial Technology Major in Automotive")
        computer_index = pdf_text.index("Bachelor of Industrial Technology Major in Computer Technology")
        self.assertLess(automotive_index, computer_index)
