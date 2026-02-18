from django import template

register = template.Library()


@register.filter
def avatar_color(index):
    """Return a hex color for avatar backgrounds based on index."""
    colors = [
        '#7C9070', '#5B9BD5', '#9B8AA8', '#C9B8A8',
        '#D4845E', '#6B8E8E', '#B87C7C',
    ]
    return colors[int(index) % len(colors)]


@register.filter
def initials(username):
    """Return two-letter initials for a username."""
    if not username:
        return '?'
    name = username.strip()
    if len(name) <= 1:
        return name.upper()
    return (name[0] + name[-1]).upper()
