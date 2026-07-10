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


def render_edition_body(data):
    meta = data["meta"]
    parts = [render_masthead(meta)]

    gotd = data.get("game_of_the_day")
    if gotd:
        parts.append(
            '<section class="game-of-the-day">'
            '<h2 class="section__label">⭐ The Game of the Day</h2>'
            '<h3 class="gotd__headline">' + render_inline(gotd["headline"]) + '</h3>'
            '<p class="gotd__subtitle">' + render_inline(gotd["subtitle"]) + '</p>'
            + render_body(gotd["body"])
            + '</section>'
        )

    countdown = data.get("countdown")
    if countdown:
        parts.append(
            '<section class="countdown"><p class="countdown__line">'
            + "{} days until ".format(countdown["days_remaining"])
            + render_inline(countdown["milestone"])
            + " (" + render_inline(countdown["target_date"]) + ")."
            + '</p></section>'
        )

    news = data.get("news") or []
    if news:
        items = "".join(
            '<div class="news__item"><h3 class="news__subhead">'
            + render_inline(n["subhead"]) + '</h3>' + render_body(n["body"]) + '</div>'
            for n in news
        )
        parts.append(
            '<section class="news"><h2 class="section__label">'
            '\U0001f4dc News Around the League</h2>' + items + '</section>'
        )

    card = data.get("rest_of_the_card") or []
    if card:
        items = "".join(
            '<div class="card__game"><h3 class="card__headline">'
            + render_inline(g["headline"]) + '</h3>' + render_body(g["body"]) + '</div>'
            for g in card
        )
        parts.append(
            '<section class="rest-of-the-card"><h2 class="section__label">'
            '\U0001f4cb The Rest of the Card</h2>' + items + '</section>'
        )

    parts.append(
        '<section class="desk-note">'
        + render_body(data["desk_note"])
        + '<p class="signoff">~ THE HERALD ~</p></section>'
    )
    return "".join(parts)


def render_edition(data, base_template):
    title = "The Morning Horsehide Herald — " + data["meta"]["date_display"]
    return render_page(title, render_edition_body(data), base_template)
