from django import template
from django.utils.safestring import mark_safe

from content.richtext import richtext_to_plaintext, sanitize_richtext


register = template.Library()


@register.filter
def safe_richtext(value):
    return mark_safe(sanitize_richtext(value))


@register.filter
def plain_richtext(value):
    return richtext_to_plaintext(value)
