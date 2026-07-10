"""The Morning Horsehide Herald renderer: edition JSON -> static HTML."""

import html
import re
import string

_STRONG = re.compile(r"\*\*(.+?)\*\*")
_EM = re.compile(r"\*(.+?)\*")


def render_inline(text):
    """Escape HTML, then apply the *em* / **strong** convention. No block tags."""
    escaped = html.escape(text, quote=False)
    escaped = _STRONG.sub(r"<strong>\1</strong>", escaped)
    escaped = _EM.sub(r"<em>\1</em>", escaped)
    return escaped


def render_body(text):
    """Render prose as one or more <p> blocks split on blank lines."""
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    return "".join("<p>{}</p>".format(render_inline(b)) for b in blocks)


_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def validate(data, schema):
    """Validate data against the supported JSON Schema subset. Raises ValueError."""
    _validate_node(data, schema, "$")


def _validate_node(value, schema, path):
    types = schema.get("type")
    if isinstance(types, str):
        types = [types]
    if types is not None and not any(_TYPE_CHECKS[t](value) for t in types if t in _TYPE_CHECKS):
        raise ValueError("{}: expected {}, got {}".format(path, types, type(value).__name__))
    if value is None:
        return
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError("{}: {!r} not in {}".format(path, value, schema["enum"]))
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                raise ValueError("{}: missing required key '{}'".format(path, key))
        for key, subschema in schema.get("properties", {}).items():
            if key in value:
                _validate_node(value[key], subschema, "{}.{}".format(path, key))
    elif isinstance(value, list):
        item_schema = schema.get("items")
        if item_schema is not None:
            for i, item in enumerate(value):
                _validate_node(item, item_schema, "{}[{}]".format(path, i))


_MASTHEAD_HEAD = (
    '<h1 class="masthead__title">⚾ THE MORNING HORSEHIDE HERALD ⚾</h1>'
    '<p class="masthead__motto">"Every Score Set Down, No Deed Unsung"</p>'
    '<p class="masthead__subtitle">~ Being a Faithful Daily Chronicle of the National Pastime ~</p>'
)


def render_page(title, body_html, base_template):
    return string.Template(base_template).safe_substitute(
        title=html.escape(title, quote=False), body=body_html
    )


def render_masthead(meta):
    if meta["mode"] == "in_season":
        n = meta["contests_reported"]
        note = "Reporting {} contest{} from the day prior.".format(n, "" if n == 1 else "s")
    else:
        note = "No contests this day; the hot stove burns bright."
    line = "{} &middot; No. {} &middot; {}, {}".format(
        render_inline(meta["volume"]),
        meta["edition_number"],
        render_inline(meta["weekday"]),
        render_inline(meta["date_display"]),
    )
    return (
        '<header class="masthead">'
        + _MASTHEAD_HEAD
        + '<p class="masthead__line">' + line + '</p>'
        + '<p class="masthead__note">' + note + '</p>'
        + '</header>'
    )
