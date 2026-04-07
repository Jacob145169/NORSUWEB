from __future__ import annotations

from posixpath import normpath
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree as ET


SPREADSHEET_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "doc_rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkg_rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


class WorkbookReadError(ValueError):
    pass


def load_first_sheet_rows(file_obj):
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)

    try:
        with ZipFile(file_obj) as workbook_archive:
            shared_strings = _load_shared_strings(workbook_archive)
            worksheet_path = _resolve_first_worksheet_path(workbook_archive)
            worksheet_root = ET.fromstring(workbook_archive.read(worksheet_path))
    except BadZipFile as exc:
        raise WorkbookReadError("The uploaded file is not a valid Excel workbook.") from exc
    except KeyError as exc:
        raise WorkbookReadError("The uploaded workbook is missing the required worksheet data.") from exc
    except ET.ParseError as exc:
        raise WorkbookReadError("The uploaded workbook could not be read.") from exc
    finally:
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)

    return _parse_rows(worksheet_root, shared_strings)


def _load_shared_strings(workbook_archive):
    try:
        root = ET.fromstring(workbook_archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []

    values = []
    for string_item in root.findall("main:si", SPREADSHEET_NS):
        text = "".join(string_item.itertext())
        values.append(text)
    return values


def _resolve_first_worksheet_path(workbook_archive):
    workbook_root = ET.fromstring(workbook_archive.read("xl/workbook.xml"))
    sheets = workbook_root.findall("main:sheets/main:sheet", SPREADSHEET_NS)
    if not sheets:
        raise WorkbookReadError("The workbook does not contain any sheets.")

    first_sheet = sheets[0]
    relation_id = first_sheet.get(f"{{{SPREADSHEET_NS['doc_rel']}}}id")
    if not relation_id:
        raise WorkbookReadError("The first sheet could not be located.")

    relationships_root = ET.fromstring(workbook_archive.read("xl/_rels/workbook.xml.rels"))
    target = None
    for relationship in relationships_root.findall("pkg_rel:Relationship", SPREADSHEET_NS):
        if relationship.get("Id") == relation_id:
            target = relationship.get("Target")
            break

    if not target:
        raise WorkbookReadError("The first sheet could not be opened.")

    normalized_target = normpath(target).lstrip("/")
    if normalized_target.startswith("xl/"):
        return normalized_target
    return f"xl/{normalized_target}"


def _parse_rows(worksheet_root, shared_strings):
    sheet_data = worksheet_root.find("main:sheetData", SPREADSHEET_NS)
    if sheet_data is None:
        return []

    parsed_rows = []
    for row in sheet_data.findall("main:row", SPREADSHEET_NS):
        values_by_index = {}

        for position, cell in enumerate(row.findall("main:c", SPREADSHEET_NS)):
            reference = cell.get("r", "")
            column_letters = "".join(character for character in reference if character.isalpha())
            column_index = _column_letters_to_index(column_letters) if column_letters else position
            values_by_index[column_index] = _read_cell_value(cell, shared_strings)

        if not values_by_index:
            parsed_rows.append([])
            continue

        max_index = max(values_by_index)
        parsed_rows.append([values_by_index.get(index, "") for index in range(max_index + 1)])

    return parsed_rows


def _read_cell_value(cell, shared_strings):
    cell_type = cell.get("t")

    if cell_type == "inlineStr":
        inline_node = cell.find("main:is", SPREADSHEET_NS)
        return "".join(inline_node.itertext()).strip() if inline_node is not None else ""

    raw_value = cell.findtext("main:v", default="", namespaces=SPREADSHEET_NS)
    if raw_value is None:
        raw_value = ""

    if cell_type == "s":
        try:
            return shared_strings[int(raw_value)].strip()
        except (ValueError, IndexError):
            return ""

    if cell_type == "b":
        return "TRUE" if raw_value == "1" else "FALSE"

    return raw_value.strip()


def _column_letters_to_index(column_letters):
    result = 0
    for character in column_letters.upper():
        result = (result * 26) + (ord(character) - ord("A") + 1)
    return max(result - 1, 0)
