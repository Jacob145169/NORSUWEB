from __future__ import annotations

import re
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse


ALLOWED_TAGS = {
    "a",
    "blockquote",
    "br",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "li",
    "ol",
    "p",
    "span",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
}
VOID_TAGS = {"br"}
SKIP_CONTENT_TAGS = {"script", "style", "iframe", "object", "embed"}
BLOCK_TAGS = {"blockquote", "br", "div", "h1", "h2", "h3", "li", "ol", "p", "table", "tr", "ul"}
GLOBAL_ALLOWED_ATTRIBUTES = {"style"}
TAG_ALLOWED_ATTRIBUTES = {
    "a": {"href", "rel", "target"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
}
ALLOWED_CSS_PROPERTIES = {
    "color",
    "font-family",
    "font-size",
    "text-align",
    "text-decoration",
}
COLOR_VALUE_RE = re.compile(
    r"^(#[0-9a-fA-F]{3,8}|rgb(a)?\([\d\s.,%]+\)|hsl(a)?\([\d\s.,%]+\)|[a-zA-Z]+)$"
)
FONT_SIZE_VALUE_RE = re.compile(r"^\d+(\.\d+)?(px|pt|em|rem|%)$")
FONT_FAMILY_VALUE_RE = re.compile(r'^[a-zA-Z0-9\s,"\047-]+$')
TEXT_DECORATION_RE = re.compile(r"^(underline|none|line-through)$")
VALID_TEXT_ALIGNMENTS = {"left", "center", "right", "justify"}
VALID_URL_SCHEMES = {"http", "https", "mailto", "tel"}


def sanitize_richtext(value: str | None) -> str:
    if not value:
        return ""

    sanitizer = RichTextSanitizer()
    sanitizer.feed(value)
    sanitizer.close()
    return sanitizer.render()


def richtext_to_plaintext(value: str | None) -> str:
    sanitized = sanitize_richtext(value)
    if not sanitized:
        return ""

    text = re.sub(r"<br\s*/?>", " ", sanitized)
    text = re.sub(r"</?(blockquote|div|h1|h2|h3|li|ol|p|table|tbody|td|th|thead|tr|ul)\b[^>]*>", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


class RichTextSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()

        if tag in SKIP_CONTENT_TAGS:
            self.skip_depth += 1
            return

        if self.skip_depth or tag not in ALLOWED_TAGS:
            return

        cleaned_attrs = self._sanitize_attributes(tag, attrs)
        attr_html = "".join(
            f' {name}="{escape(value, quote=True)}"'
            for name, value in cleaned_attrs
        )
        self.parts.append(f"<{tag}{attr_html}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if tag in SKIP_CONTENT_TAGS:
            if self.skip_depth:
                self.skip_depth -= 1
            return

        if self.skip_depth or tag not in ALLOWED_TAGS or tag in VOID_TAGS:
            return

        self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(escape(data))

    def handle_entityref(self, name: str) -> None:
        if not self.skip_depth:
            self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self.skip_depth:
            self.parts.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        return

    def render(self) -> str:
        return "".join(self.parts)

    def _sanitize_attributes(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> list[tuple[str, str]]:
        allowed_attributes = GLOBAL_ALLOWED_ATTRIBUTES | TAG_ALLOWED_ATTRIBUTES.get(tag, set())
        cleaned_attrs: list[tuple[str, str]] = []

        for name, raw_value in attrs:
            if raw_value is None:
                continue

            attr_name = name.lower()
            attr_value = raw_value.strip()

            if attr_name not in allowed_attributes or not attr_value:
                continue

            if attr_name == "style":
                style_value = sanitize_inline_style(attr_value)
                if style_value:
                    cleaned_attrs.append((attr_name, style_value))
                continue

            if tag == "a":
                if attr_name == "href":
                    href = sanitize_url(attr_value)
                    if href:
                        cleaned_attrs.append((attr_name, href))
                    continue

                if attr_name == "target":
                    if attr_value == "_blank":
                        cleaned_attrs.append((attr_name, attr_value))
                    continue

                if attr_name == "rel":
                    continue

            if attr_name in {"colspan", "rowspan"}:
                if attr_value.isdigit():
                    cleaned_attrs.append((attr_name, attr_value))
                continue

            cleaned_attrs.append((attr_name, attr_value))

        if tag == "a":
            attr_names = {name for name, _ in cleaned_attrs}
            if "target" in attr_names:
                cleaned_attrs = [(name, value) for name, value in cleaned_attrs if name != "rel"]
                cleaned_attrs.append(("rel", "noopener noreferrer"))

        return cleaned_attrs


def sanitize_url(value: str) -> str:
    parsed = urlparse(value)

    if parsed.scheme and parsed.scheme.lower() not in VALID_URL_SCHEMES:
        return ""

    if parsed.scheme.lower() == "javascript":
        return ""

    return value


def sanitize_inline_style(style_value: str) -> str:
    sanitized_rules: list[str] = []

    for declaration in style_value.split(";"):
        if ":" not in declaration:
            continue

        property_name, raw_value = declaration.split(":", 1)
        css_property = property_name.strip().lower()
        css_value = raw_value.strip()

        if css_property not in ALLOWED_CSS_PROPERTIES:
            continue

        if css_property in {"color"} and COLOR_VALUE_RE.fullmatch(css_value):
            sanitized_rules.append(f"{css_property}: {css_value}")
        elif css_property == "font-size" and FONT_SIZE_VALUE_RE.fullmatch(css_value):
            sanitized_rules.append(f"{css_property}: {css_value}")
        elif css_property == "font-family" and FONT_FAMILY_VALUE_RE.fullmatch(css_value):
            sanitized_rules.append(f"{css_property}: {css_value}")
        elif css_property == "text-align" and css_value.lower() in VALID_TEXT_ALIGNMENTS:
            sanitized_rules.append(f"{css_property}: {css_value.lower()}")
        elif css_property == "text-decoration" and TEXT_DECORATION_RE.fullmatch(css_value.lower()):
            sanitized_rules.append(f"{css_property}: {css_value.lower()}")

    return "; ".join(sanitized_rules)
