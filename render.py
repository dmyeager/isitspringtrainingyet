"""The Morning Horsehide Herald renderer: edition JSON -> static HTML."""

import html
import re

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
