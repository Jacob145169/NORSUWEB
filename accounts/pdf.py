from __future__ import annotations

import io
import textwrap

from PIL import Image, UnidentifiedImageError


# Long bond paper in portrait: 8.5 x 13 inches = 612 x 936 points.
PAGE_WIDTH = 612
PAGE_HEIGHT = 936
LEFT_MARGIN = 24
TOP_MARGIN = 36
BOTTOM_MARGIN = 36
BODY_FONT_SIZE = 9
BODY_LINE_HEIGHT = 13
BODY_WRAP_WIDTH = 88
COURSE_LINE_PREFIX = "__COURSE__:"
LOGO_MAX_WIDTH = 286
LOGO_MAX_HEIGHT = 286
LOGO_OPACITY = 0.08


def build_alumni_pdf(*, title, subtitle_lines, record_lines, footer_text, logo_file=None):
    logo_image = _prepare_logo_image(logo_file)
    available_body_height = PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN - 78
    lines_per_page = max(int(available_body_height // BODY_LINE_HEIGHT), 1)
    pages = _chunk_lines(record_lines, lines_per_page)

    object_bodies = []
    catalog_id = 1
    pages_id = 2
    regular_font_id = 3
    bold_font_id = 4
    mono_font_id = 5

    object_bodies.extend(
        [
            _catalog_body(pages_id),
            _pages_body([]),
            _font_body("Helvetica"),
            _font_body("Helvetica-Bold"),
            _font_body("Courier"),
        ]
    )

    page_ids = []
    next_object_id = 6
    logo_image_object_id = None
    graphics_state_object_id = None

    if logo_image:
        logo_image_object_id = next_object_id
        object_bodies.append(_image_stream_body(logo_image))
        graphics_state_object_id = next_object_id + 1
        object_bodies.append(_graphics_state_body())
        next_object_id += 2

    for page_number, page_lines in enumerate(pages, start=1):
        page_id = next_object_id
        content_id = next_object_id + 1
        next_object_id += 2
        page_ids.append(page_id)

        content_stream = _page_stream(
            title=title,
            subtitle_lines=subtitle_lines,
            body_lines=page_lines,
            footer_text=footer_text,
            page_number=page_number,
            page_count=len(pages),
            logo_image=logo_image if page_number == 1 else None,
        )
        object_bodies.append(
            _page_body(
                parent_id=pages_id,
                content_id=content_id,
                regular_font_id=regular_font_id,
                bold_font_id=bold_font_id,
                mono_font_id=mono_font_id,
                image_object_id=logo_image_object_id,
                graphics_state_object_id=graphics_state_object_id,
            )
        )
        object_bodies.append(_stream_body(content_stream))

    object_bodies[1] = _pages_body(page_ids)
    return _assemble_pdf(object_bodies)


def build_alumni_record_lines(alumni_items):
    lines = []
    current_course = None
    course_index = 0

    for alumnus in alumni_items:
        course_name = _course_display_name(alumnus.course_program)

        if course_name != current_course:
            if lines:
                lines.append("")
            lines.append(f"{COURSE_LINE_PREFIX}{course_name}")
            lines.append("")
            current_course = course_name
            course_index = 1
        else:
            course_index += 1

        lines.extend(
            [
                f"{course_index}. {alumnus.full_name}",
                f"   ID Number: {alumnus.id_number or 'Not set'}    Batch: {alumnus.batch_year}",
                *_wrap_line(
                    f"   Email: {alumnus.email or '-'}    Contact: {alumnus.contact_number or '-'}",
                    BODY_WRAP_WIDTH,
                ),
            ]
        )

        if alumnus.job_title or alumnus.company_name:
            employment_line = alumnus.job_title or ""
            if alumnus.job_title and alumnus.company_name:
                employment_line += " at "
            if alumnus.company_name:
                employment_line += alumnus.company_name
            lines.extend(_wrap_line(f"   Employment: {employment_line}", BODY_WRAP_WIDTH))

        lines.append("")

    if not lines:
        lines = ["No alumni records match the current filters."]

    return lines


def _wrap_line(text, width):
    wrapped = textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False)
    return wrapped or [text]


def _course_display_name(course_program):
    text = str(course_program or "").strip()
    if " - " in text:
        return text.split(" - ", 1)[1].strip() or text
    return text


def _chunk_lines(lines, lines_per_page):
    if not lines:
        return [[]]
    return [lines[index:index + lines_per_page] for index in range(0, len(lines), lines_per_page)]


def _catalog_body(pages_id):
    return f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii")


def _pages_body(page_ids):
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    return f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")


def _font_body(base_font):
    return f"<< /Type /Font /Subtype /Type1 /BaseFont /{base_font} >>".encode("ascii")


def _page_body(
    *,
    parent_id,
    content_id,
    regular_font_id,
    bold_font_id,
    mono_font_id,
    image_object_id=None,
    graphics_state_object_id=None,
):
    xobject_resource = f" /XObject << /Im1 {image_object_id} 0 R >>" if image_object_id else ""
    graphics_state_resource = (
        f" /ExtGState << /GS1 {graphics_state_object_id} 0 R >>" if graphics_state_object_id else ""
    )
    return (
        f"<< /Type /Page /Parent {parent_id} 0 R "
        f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
        f"/Resources << /Font << /F1 {regular_font_id} 0 R /F2 {bold_font_id} 0 R /F3 {mono_font_id} 0 R >>{xobject_resource}{graphics_state_resource} >> "
        f"/Contents {content_id} 0 R >>"
    ).encode("ascii")


def _stream_body(stream_bytes):
    return b"<< /Length " + str(len(stream_bytes)).encode("ascii") + b" >>\nstream\n" + stream_bytes + b"\nendstream"


def _image_stream_body(image):
    dictionary = (
        f"<< /Type /XObject /Subtype /Image /Width {image['width']} /Height {image['height']} "
        f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(image['bytes'])} >>\n"
    ).encode("ascii")
    return dictionary + b"stream\n" + image["bytes"] + b"\nendstream"


def _graphics_state_body():
    return f"<< /Type /ExtGState /ca {LOGO_OPACITY:.2f} /CA {LOGO_OPACITY:.2f} >>".encode("ascii")


def _page_stream(*, title, subtitle_lines, body_lines, footer_text, page_number, page_count, logo_image=None):
    commands = []
    title_y = PAGE_HEIGHT - 46
    subtitle_y = PAGE_HEIGHT - 68
    body_y = PAGE_HEIGHT - 112

    if logo_image:
        logo_x = (PAGE_WIDTH - logo_image["width"]) / 2
        logo_y = (PAGE_HEIGHT - logo_image["height"]) / 2
        commands.extend(
            [
                "q",
                "/GS1 gs",
                f"{logo_image['width']} 0 0 {logo_image['height']} {logo_x:.2f} {logo_y:.2f} cm",
                "/Im1 Do",
                "Q",
            ]
        )

    commands.extend(_text_block("F2", 16, LEFT_MARGIN, title_y, [title], 12, center=True))
    commands.extend(_text_block("F1", 9, LEFT_MARGIN, subtitle_y, subtitle_lines, center=True))
    commands.extend(_mixed_body_text_block(LEFT_MARGIN, body_y, body_lines))
    commands.extend(
        _text_block(
            "F1",
            8,
            LEFT_MARGIN,
            24,
            [f"{footer_text}    Page {page_number} of {page_count}"],
            10,
        )
    )
    return "\n".join(commands).encode("latin-1", "replace")


def _mixed_body_text_block(x, y, lines):
    commands = []
    current_y = y

    for line in lines:
        font_name = "F3"
        font_size = BODY_FONT_SIZE
        text = line

        if line.startswith(COURSE_LINE_PREFIX):
            font_name = "F2"
            font_size = 11
            text = line[len(COURSE_LINE_PREFIX):]

        commands.extend(_text_block(font_name, font_size, x, current_y, [text], BODY_LINE_HEIGHT))
        current_y -= BODY_LINE_HEIGHT

    return commands


def _text_block(font_name, font_size, x, y, lines, line_height=12, center=False):
    if not lines:
        return []

    if center:
        commands = []
        current_y = y
        for line in lines:
            text_width = _estimated_text_width(line, font_size)
            draw_x = (PAGE_WIDTH - text_width) / 2
            commands.extend(
                [
                    "BT",
                    f"/{font_name} {font_size} Tf",
                    f"{line_height} TL",
                    f"{draw_x:.2f} {current_y} Td",
                    f"({_pdf_escape(line)}) Tj",
                    "ET",
                ]
            )
            current_y -= line_height
        return commands

    commands = [
        "BT",
        f"/{font_name} {font_size} Tf",
        f"{line_height} TL",
        f"{x} {y} Td",
    ]

    for index, line in enumerate(lines):
        if index:
            commands.append("T*")
        commands.append(f"({_pdf_escape(line)}) Tj")
    commands.append("ET")
    return commands


def _estimated_text_width(text, font_size):
    return len(str(text or "")) * font_size * 0.52


def _prepare_logo_image(logo_file):
    if not logo_file:
        return None

    try:
        logo_file.open("rb")
        with Image.open(logo_file) as image:
            image = image.convert("RGB")
            image.thumbnail((LOGO_MAX_WIDTH, LOGO_MAX_HEIGHT))
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=88, optimize=True)
            return {
                "bytes": buffer.getvalue(),
                "width": image.width,
                "height": image.height,
            }
    except (FileNotFoundError, OSError, UnidentifiedImageError):
        return None
    finally:
        try:
            logo_file.close()
        except Exception:
            pass


def _pdf_escape(text):
    escaped = str(text or "").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return escaped.replace("\r", " ").replace("\n", " ")


def _assemble_pdf(object_bodies):
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]

    for index, body in enumerate(object_bodies, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(object_bodies) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    pdf.extend(
        (
            f"trailer\n<< /Size {len(object_bodies) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode("ascii")
    )
    return bytes(pdf)
