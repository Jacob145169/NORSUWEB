from datetime import timedelta
import io
import shutil
from zipfile import ZIP_DEFLATED, ZipFile
from pathlib import Path
from xml.sax.saxutils import escape

from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone

from PIL import Image

from .forms import DepartmentForm
from alumni.models import Alumni
from content.models import Announcement, Event, News, PublicationStatus
from .models import RoleChoices, User
from academics.models import Instructor, Program, ProgramUniformImage
from departments.models import CalendarImage, Department, SchoolInfo


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


def build_test_video(*, name="test.mp4"):
    return SimpleUploadedFile(name, b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41", content_type="video/mp4")


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
        self.assertEqual(self.department.theme_color, "#12345b")
        self.assertEqual(self.department.theme_color_secondary, "")

    def test_department_profile_form_hides_gradient_color_fields(self):
        self.client.force_login(self.department_admin)

        response = self.client.get(reverse("accounts:department_leadership_update"))

        self.assertContains(response, "<label for=\"id_mission\" class=\"form-label\">Department Mission</label>", html=False)
        self.assertContains(response, "<label for=\"id_vision\" class=\"form-label\">Department Vision</label>", html=False)
        self.assertNotContains(response, "<label for=\"id_course_uniform_description\" class=\"form-label\">Course Uniform Details</label>", html=False)
        self.assertNotContains(response, "<label for=\"id_course_uniform_image\" class=\"form-label\">Course Uniform Image</label>", html=False)
        self.assertNotContains(response, "<label for=\"id_theme_color\" class=\"form-label\">Gradient Color 1</label>", html=False)
        self.assertNotContains(response, "<label for=\"id_theme_color_secondary\" class=\"form-label\">Gradient Color 2</label>", html=False)

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
        self.assertNotContains(response, "<label for=\"id_course_uniform_description\" class=\"form-label\">Course Uniform Details</label>", html=False)
        self.assertNotContains(response, "<label for=\"id_course_uniform_image\" class=\"form-label\">Course Uniform Image</label>", html=False)


@override_settings(MEDIA_ROOT=str(TEST_MEDIA_ROOT))
class ProgramUniformManagementTests(TestCase):
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
            is_active=True,
        )
        self.department_admin = User.objects.create_user(
            username="cit_admin",
            email="cit@example.com",
            password="testpass123",
            full_name="CIT Admin",
            role=RoleChoices.DEPARTMENT_ADMIN,
            department=self.department,
        )
        self.super_admin = User.objects.create_user(
            username="super_admin_programs",
            email="superprograms@example.com",
            password="testpass123",
            full_name="Super Admin Programs",
            role=RoleChoices.SUPER_ADMIN,
        )
        self.program = Program.objects.create(
            program_code="BSCT",
            program_name="Bachelor of Science in Computer Technology",
            description="Program description.",
            department=self.department,
        )

    def test_department_admin_can_update_program_uniform_fields(self):
        self.client.force_login(self.department_admin)

        response = self.client.post(
            reverse("accounts:program_update", args=[self.program.pk]),
            {
                "program_code": "BSCT",
                "program_name": "Bachelor of Science in Computer Technology",
                "description": "Updated program description.",
                "course_uniform_description": "Wear the prescribed CIT uniform with the official patch during laboratory classes.",
                "course_uniform_images": [
                    build_test_image(900, 1200, name="program-uniform-front.png"),
                    build_test_image(900, 1200, name="program-uniform-back.png"),
                ],
                "department": str(self.department.pk),
            },
        )

        self.assertRedirects(response, reverse("accounts:program_list"))
        self.program.refresh_from_db()
        self.assertEqual(
            self.program.course_uniform_description,
            "Wear the prescribed CIT uniform with the official patch during laboratory classes.",
        )
        self.assertEqual(self.program.uniform_images.count(), 2)

    def test_department_admin_program_form_shows_uniform_fields(self):
        self.client.force_login(self.department_admin)

        response = self.client.get(reverse("accounts:program_update", args=[self.program.pk]))

        self.assertContains(response, "<label for=\"id_course_uniform_description\" class=\"form-label\">Course Uniform Details</label>", html=False)
        self.assertContains(response, "<label for=\"id_course_uniform_images\" class=\"form-label\">Course Uniform Pictures</label>", html=False)

    def test_super_admin_program_form_hides_uniform_fields(self):
        self.client.force_login(self.super_admin)

        response = self.client.get(reverse("accounts:program_update", args=[self.program.pk]))

        self.assertNotContains(response, "<label for=\"id_course_uniform_description\" class=\"form-label\">Course Uniform Details</label>", html=False)
        self.assertNotContains(response, "<label for=\"id_course_uniform_images\" class=\"form-label\">Course Uniform Pictures</label>", html=False)

    def test_department_admin_can_remove_existing_program_uniform_picture(self):
        uniform_image = ProgramUniformImage.objects.create(
            program=self.program,
            image=build_test_image(900, 1200, name="existing-uniform.png"),
            sort_order=0,
        )
        self.client.force_login(self.department_admin)

        response = self.client.post(
            reverse("accounts:program_update", args=[self.program.pk]),
            {
                "program_code": "BSCT",
                "program_name": "Bachelor of Science in Computer Technology",
                "description": "Program description.",
                "course_uniform_description": "",
                "remove_course_uniform_images": [str(uniform_image.pk)],
                "department": str(self.department.pk),
            },
        )

        self.assertRedirects(response, reverse("accounts:program_list"))
        self.assertFalse(ProgramUniformImage.objects.filter(pk=uniform_image.pk).exists())


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


class SuperAdminDashboardViewTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            username="super_admin_dashboard",
            email="superdashboard@example.com",
            password="testpass123",
            full_name="Super Admin Dashboard",
            role=RoleChoices.SUPER_ADMIN,
        )
        self.department = Department.objects.create(
            name="College of Engineering",
            code="COE",
            description="Engineering department.",
            theme_color="#12345b",
            is_active=True,
        )
        self.department_admin = User.objects.create_user(
            username="coe_admin_dashboard",
            email="coedashboard@example.com",
            password="testpass123",
            full_name="COE Admin Dashboard",
            role=RoleChoices.DEPARTMENT_ADMIN,
            department=self.department,
        )
        Program.objects.create(
            program_code="BSIT",
            program_name="BS Information Technology",
            department=self.department,
        )
        Instructor.objects.create(
            full_name="Dr. Elena Ramos",
            department=self.department,
        )
        SchoolInfo.get_solo()
        Announcement.objects.create(
            title="University advisory",
            content="Draft advisory for review.",
            publication_status=PublicationStatus.DRAFT,
        )
        News.objects.create(
            title="Campus innovation fair",
            content="<p>Innovation fair article.</p>",
            department=self.department,
            posted_by=self.department_admin,
        )
        Event.objects.create(
            title="Research Congress",
            description="<p>Research event for the campus.</p>",
            event_date=timezone.now() + timedelta(days=4),
            location="Main Hall",
            department=self.department,
            posted_by=self.department_admin,
        )
        Alumni.objects.create(
            full_name="Maria Santos",
            batch_year=2021,
            course_program="BS Information Technology",
            department=self.department,
            email="maria@example.com",
            contact_number="09123456789",
            address="Bayawan City",
            is_public=False,
        )

    def test_super_admin_dashboard_shows_redesigned_sections(self):
        self.client.force_login(self.super_admin)

        response = self.client.get(reverse("accounts:super_admin_dashboard"))

        self.assertContains(response, "Super Admin Overview")
        self.assertContains(response, "Recent activity")
        self.assertNotContains(response, "Pending approvals")
        self.assertNotContains(response, "Quick links")
        self.assertNotContains(response, "Add Department")
        self.assertNotContains(response, "Add Department Admin")
        self.assertNotContains(response, "Publish Update")
        self.assertContains(response, "Campus innovation fair")
        self.assertNotContains(response, f'href="{reverse("accounts:department_create")}"')
        self.assertNotContains(response, f'href="{reverse("accounts:department_admin_create")}"')
        self.assertNotContains(response, f'href="{reverse("accounts:update_create")}"')


class DepartmentAdminManagementViewTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            username="super_admin_accounts",
            email="super-admin-accounts@example.com",
            password="testpass123",
            full_name="Super Admin Accounts",
            role=RoleChoices.SUPER_ADMIN,
        )
        self.department = Department.objects.create(
            name="College of Agriculture and Forestry",
            code="CAF",
            description="Agriculture and forestry department.",
            theme_color="#1b5e20",
            is_active=True,
        )
        self.other_department = Department.objects.create(
            name="College of Arts and Sciences",
            code="CAS",
            description="Arts and sciences department.",
            theme_color="#283593",
            is_active=True,
        )
        self.department_admin = User.objects.create_user(
            username="CAF_ADMIN",
            email="admincaf@norsu.edu.ph",
            password="OldPass123!",
            full_name="Department Admin CAF",
            role=RoleChoices.DEPARTMENT_ADMIN,
            department=self.department,
        )

    def test_department_admin_list_shows_departments_waiting_for_assignment(self):
        self.client.force_login(self.super_admin)

        response = self.client.get(reverse("accounts:department_admin_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Departments Without Assigned Admins")
        self.assertContains(response, "College of Arts and Sciences")
        self.assertContains(
            response,
            f'{reverse("accounts:department_admin_create")}?department={self.other_department.pk}',
        )
        self.assertNotContains(
            response,
            f'{reverse("accounts:department_admin_create")}?department={self.department.pk}',
        )

    def test_department_admin_create_form_shows_only_departments_without_admins_and_prefills_selected_department(self):
        self.client.force_login(self.super_admin)

        response = self.client.get(
            reverse("accounts:department_admin_create"),
            {"department": self.other_department.pk},
        )

        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertQuerySetEqual(
            form.fields["department"].queryset.order_by("pk"),
            Department.objects.filter(pk=self.other_department.pk).order_by("pk"),
            transform=lambda department: department,
        )
        self.assertEqual(str(form["department"].value()), str(self.other_department.pk))

    def test_department_is_locked_on_update_form(self):
        self.client.force_login(self.super_admin)

        response = self.client.get(reverse("accounts:department_admin_update", args=[self.department_admin.pk]))

        form = response.context["form"]
        self.assertTrue(form.fields["department"].disabled)
        self.assertQuerySetEqual(
            form.fields["department"].queryset.order_by("pk"),
            Department.objects.filter(pk=self.department.pk).order_by("pk"),
            transform=lambda department: department,
        )
        self.assertContains(response, "College of Agriculture and Forestry")
        self.assertNotContains(response, "College of Arts and Sciences")

    def test_super_admin_can_update_department_admin_username_without_changing_password(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(
            reverse("accounts:department_admin_update", args=[self.department_admin.pk]),
            {
                "username": "CAF_ADMIN_UPDATED",
                "full_name": "Department Admin CAF",
                "email": "admincaf@norsu.edu.ph",
                "department": self.department.pk,
                "is_active": "on",
                "password1": "",
                "password2": "",
            },
        )

        self.assertRedirects(response, reverse("accounts:department_admin_list"))
        self.department_admin.refresh_from_db()
        self.assertEqual(self.department_admin.username, "CAF_ADMIN_UPDATED")
        self.assertTrue(self.department_admin.check_password("OldPass123!"))
        self.assertEqual(self.department_admin.department, self.department)

    def test_super_admin_can_change_department_admin_password_from_update_form(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(
            reverse("accounts:department_admin_update", args=[self.department_admin.pk]),
            {
                "username": "CAF_ADMIN_RENAMED",
                "full_name": "Department Admin CAF",
                "email": "admincaf@norsu.edu.ph",
                "department": self.department.pk,
                "is_active": "on",
                "password1": "NewPass123!",
                "password2": "NewPass123!",
            },
        )

        self.assertRedirects(response, reverse("accounts:department_admin_list"))
        self.department_admin.refresh_from_db()
        self.assertEqual(self.department_admin.username, "CAF_ADMIN_RENAMED")
        self.assertTrue(self.department_admin.check_password("NewPass123!"))
        self.assertFalse(self.department_admin.check_password("OldPass123!"))
        self.assertEqual(self.department_admin.department, self.department)

    def test_posted_department_change_is_ignored_on_update_form(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(
            reverse("accounts:department_admin_update", args=[self.department_admin.pk]),
            {
                "username": "CAF_ADMIN_LOCKED",
                "full_name": "Department Admin CAF",
                "email": "admincaf@norsu.edu.ph",
                "department": self.other_department.pk,
                "is_active": "on",
                "password1": "",
                "password2": "",
            },
        )

        self.assertRedirects(response, reverse("accounts:department_admin_list"))
        self.department_admin.refresh_from_db()
        self.assertEqual(self.department_admin.username, "CAF_ADMIN_LOCKED")
        self.assertEqual(self.department_admin.department, self.department)


class DepartmentManagementViewTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            username="super_admin_department_page",
            email="super-admin-departments@example.com",
            password="testpass123",
            full_name="Super Admin Department Page",
            role=RoleChoices.SUPER_ADMIN,
        )
        Department.objects.create(
            name="College of Agriculture and Forestry",
            code="CAF-LIST",
            description="Agriculture and forestry department.",
            theme_color="#1b5e20",
            is_active=True,
        )

    def test_department_management_page_shows_add_department_button_at_top(self):
        self.client.force_login(self.super_admin)

        response = self.client.get(reverse("accounts:department_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Department Management")
        self.assertContains(response, "Add Department")
        self.assertContains(response, f'href="{reverse("accounts:department_create")}"')


@override_settings(MEDIA_ROOT=str(TEST_MEDIA_ROOT))
class SchoolInfoUpdateViewTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.super_admin = User.objects.create_user(
            username="super_admin_school_info",
            email="schoolinfo@example.com",
            password="testpass123",
            full_name="Super Admin School Info",
            role=RoleChoices.SUPER_ADMIN,
        )
        self.department = Department.objects.create(
            name="College of Business",
            code="COB-SI",
            description="Business department.",
            theme_color="#12345b",
            is_active=True,
        )

    def test_department_admin_cannot_access_school_info_update(self):
        department_admin = User.objects.create_user(
            username="dept_admin_school_info",
            email="deptschoolinfo@example.com",
            password="testpass123",
            full_name="Department Admin School Info",
            role=RoleChoices.DEPARTMENT_ADMIN,
            department=self.department,
        )
        self.client.force_login(department_admin)

        response = self.client.get(reverse("accounts:school_info_update"))

        self.assertEqual(response.status_code, 403)

    def test_super_admin_can_update_strategic_goals_core_values_landing_background_and_calendar_images(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(
            reverse("accounts:school_info_update"),
            {
                "college_name": "Negros Oriental State University",
                "landing_background_image": build_test_image(1440, 900, name="homepage-hero.png"),
                "calendar_images": [
                    build_test_image(1100, 1500, name="calendar-poster-1.png"),
                    build_test_image(1100, 1500, name="calendar-poster-2.png"),
                ],
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
        self.assertTrue(bool(school_info.landing_background_image))
        self.assertEqual(CalendarImage.objects.filter(school_info=school_info).count(), 2)

    def test_uploading_new_calendar_images_replaces_existing_ones(self):
        self.client.force_login(self.super_admin)
        school_info = SchoolInfo.get_solo()
        old_image = CalendarImage.objects.create(
            school_info=school_info,
            image=build_test_image(1100, 1500, name="calendar-old.png"),
        )

        response = self.client.post(
            reverse("accounts:school_info_update"),
            {
                "college_name": "Negros Oriental State University",
                "calendar_images": [
                    build_test_image(1100, 1500, name="calendar-new-1.png"),
                    build_test_image(1100, 1500, name="calendar-new-2.png"),
                ],
                "mission": "Mission text",
                "vision": "Vision text",
                "strategic_goals": "Strategic Goals text",
                "core_values": "Core Values text",
                "quality_policy": "Quality Policy text",
                "history": "History text",
            },
        )

        self.assertRedirects(response, reverse("accounts:super_admin_dashboard"))
        self.assertFalse(CalendarImage.objects.filter(pk=old_image.pk).exists())
        self.assertEqual(CalendarImage.objects.filter(school_info=school_info).count(), 2)

    def test_super_admin_can_choose_which_current_calendar_picture_stays_first(self):
        self.client.force_login(self.super_admin)
        school_info = SchoolInfo.get_solo()
        first_image = CalendarImage.objects.create(
            school_info=school_info,
            image=build_test_image(1100, 1500, name="calendar-order-1.png"),
            sort_order=0,
        )
        second_image = CalendarImage.objects.create(
            school_info=school_info,
            image=build_test_image(1100, 1500, name="calendar-order-2.png"),
            sort_order=1,
        )

        response = self.client.post(
            reverse("accounts:school_info_update"),
            {
                "college_name": "Negros Oriental State University",
                "top_calendar_image": str(second_image.pk),
                "mission": "Mission text",
                "vision": "Vision text",
                "strategic_goals": "Strategic Goals text",
                "core_values": "Core Values text",
                "quality_policy": "Quality Policy text",
                "history": "History text",
            },
        )

        self.assertRedirects(response, reverse("accounts:super_admin_dashboard"))
        ordered_ids = list(
            CalendarImage.objects.filter(school_info=school_info).order_by("sort_order", "created_at", "pk").values_list("pk", flat=True)
        )
        self.assertEqual(ordered_ids, [second_image.pk, first_image.pk])

    def test_school_info_form_shows_calendar_strategic_goals_core_values_and_quality_policy_fields(self):
        self.client.force_login(self.super_admin)

        response = self.client.get(reverse("accounts:school_info_update"))

        self.assertContains(response, "<label for=\"id_landing_background_image\" class=\"form-label\">Landing Page Background Image</label>", html=False)
        self.assertContains(response, "<label for=\"id_calendar_images\" class=\"form-label\">NORSU Calendar Pictures</label>", html=False)
        self.assertContains(response, "Uploading new pictures replaces the current set.")
        self.assertContains(response, "Put on top")
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
                "theme_color_secondary": "#2563eb",
            },
            files={"banner_image": build_test_image(1200, 800, name="department-banner-invalid.png")},
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_normalizes_secondary_gradient_color(self):
        form = DepartmentForm(
            data={
                "name": "College of Teacher Education",
                "code": "CTED-FORM",
                "description": "Teacher education department.",
                "dean_name": "",
                "assistant_dean_name": "",
                "theme_color": "#12345B",
                "theme_color_secondary": "#2563EB",
            },
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["theme_color"], "#12345b")
        self.assertEqual(form.cleaned_data["theme_color_secondary"], "#2563eb")


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

    def test_event_list_defaults_to_published_events_and_shows_drafts_link(self):
        Event.objects.create(
            title="Published department event",
            description="Visible on the main event list.",
            department=self.department,
            event_date=timezone.now() + timedelta(days=1),
            location="Engineering Hall",
            publication_status=PublicationStatus.PUBLISHED,
        )
        Event.objects.create(
            title="Draft department event",
            description="Visible only in the drafts view.",
            department=self.department,
            event_date=timezone.now() + timedelta(days=2),
            location="Engineering Hall",
            publication_status=PublicationStatus.DRAFT,
        )

        self.client.force_login(self.department_admin)
        response = self.client.get(reverse("accounts:event_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Published department event")
        self.assertNotContains(response, "Draft department event")
        self.assertContains(response, f'href="{reverse("accounts:event_list")}?status=draft"')
        self.assertContains(response, "Drafts")

    def test_event_list_drafts_view_shows_only_department_drafts(self):
        Event.objects.create(
            title="Published department event",
            description="Should stay off the drafts list.",
            department=self.department,
            event_date=timezone.now() + timedelta(days=1),
            location="Engineering Hall",
            publication_status=PublicationStatus.PUBLISHED,
        )
        Event.objects.create(
            title="Draft department event",
            description="Should appear on the drafts list.",
            department=self.department,
            event_date=timezone.now() + timedelta(days=2),
            location="Engineering Hall",
            publication_status=PublicationStatus.DRAFT,
        )
        Event.objects.create(
            title="Other department draft event",
            description="Should not appear for this department admin.",
            department=self.other_department,
            event_date=timezone.now() + timedelta(days=3),
            location="Business Hall",
            publication_status=PublicationStatus.DRAFT,
        )

        self.client.force_login(self.department_admin)
        response = self.client.get(f"{reverse('accounts:event_list')}?status=draft")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Department Event Drafts")
        self.assertContains(response, "Draft department event")
        self.assertNotContains(response, "Published department event")
        self.assertNotContains(response, "Other department draft event")
        self.assertContains(response, reverse("accounts:event_list"))

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

    def test_shared_update_create_can_save_partial_draft(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(
            reverse("accounts:update_create"),
            {
                "content": "Draft content without a title yet.",
                "save_action": "draft",
            },
        )

        draft_news = News.objects.get(content="Draft content without a title yet.")
        self.assertRedirects(response, reverse("accounts:news_update", args=[draft_news.pk]))
        self.assertEqual(draft_news.publication_status, PublicationStatus.DRAFT)
        self.assertEqual(draft_news.title, "Untitled News Draft")

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

    def test_event_create_can_save_partial_draft(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(
            reverse("accounts:event_create"),
            {
                "description": "Draft event notes before final scheduling.",
                "save_action": "draft",
            },
        )

        draft_event = Event.objects.get(description="Draft event notes before final scheduling.")
        self.assertRedirects(response, reverse("accounts:event_update", args=[draft_event.pk]))
        self.assertEqual(draft_event.publication_status, PublicationStatus.DRAFT)
        self.assertEqual(draft_event.title, "Untitled Event Draft")
        self.assertIsNotNone(draft_event.event_date)

    def test_event_update_uses_drafts_back_link_for_draft_event(self):
        draft_event = Event.objects.create(
            title="Draft event for editing",
            description="Draft event details.",
            department=self.department,
            event_date=timezone.now() + timedelta(days=2),
            location="Engineering Hall",
            publication_status=PublicationStatus.DRAFT,
        )

        self.client.force_login(self.department_admin)
        response = self.client.get(reverse("accounts:event_update", args=[draft_event.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{reverse("accounts:event_list")}?status=draft"')

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


@override_settings(MEDIA_ROOT=str(TEST_MEDIA_ROOT))
class UpdateManagementMediaViewTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.department = Department.objects.create(
            name="College of Engineering",
            code="COE-MEDIA",
            description="Engineering department.",
            theme_color="#0f4c81",
            is_active=True,
        )
        self.super_admin = User.objects.create_user(
            username="super_admin_media",
            email="super-media@example.com",
            password="testpass123",
            full_name="Super Admin",
            role=RoleChoices.SUPER_ADMIN,
        )

    def test_shared_update_create_saves_uploaded_video(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(
            reverse("accounts:update_create"),
            {
                "title": "Campus video update",
                "content": "Video-enabled update content.",
                "video": build_test_video(name="campus-update.mp4"),
            },
        )

        self.assertRedirects(response, reverse("accounts:update_list"))
        news_item = News.objects.get(title="Campus video update")
        self.assertTrue(news_item.video.name.endswith("campus-update.mp4"))

    def test_event_create_saves_uploaded_video(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(
            reverse("accounts:event_create"),
            {
                "title": "Campus video event",
                "description": "Video-enabled event content.",
                "event_date": "2026-04-20T09:00",
                "location": "Main Auditorium",
                "video": build_test_video(name="campus-event.mp4"),
            },
        )

        self.assertRedirects(response, reverse("accounts:event_list"))
        event = Event.objects.get(title="Campus video event")
        self.assertTrue(event.video.name.endswith("campus-event.mp4"))


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
