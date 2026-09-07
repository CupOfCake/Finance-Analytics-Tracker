from django import template

register = template.Library()

@register.filter
def isk_format(value):
    """
    Format a number as Icelandic króna (ISK).
    Example: 12345 → "12.345 kr.", -5000 → "-5.000 kr."
    """
    try:
        val = int(value)
    except (ValueError, TypeError):
        return value

    sign = '-' if val < 0 else ''
    abs_val = abs(val)
    # Add dot as thousand separator
    formatted = f"{abs_val:,}".replace(',', '.')
    return f"{sign}{formatted} kr."


@register.filter
def clean_description(value):
    """If description contains ' - ' and both sides are identical, return only the first part."""
    if not value:
        return value
    if ' - ' in value:
        parts = value.split(' - ', 1)
        if len(parts) == 2 and parts[0].strip() == parts[1].strip():
            return parts[0].strip()
    return value