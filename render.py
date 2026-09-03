"""The Morning Horsehide Herald renderer: edition JSON -> static HTML."""

import html
import json
import re
import string
import sys
from pathlib import Path

_STRONG = re.compile(r"\*\*(?!\s)(.+?)(?<!\s)\*\*")
_EM = re.compile(r"\*(?!\s)(.+?)(?<!\s)\*")


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
    if "pattern" in schema and isinstance(value, str):
        if re.fullmatch(schema["pattern"], value) is None:
            raise ValueError("{}: {!r} does not match pattern {}".format(path, value, schema["pattern"]))
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


def _epithet_pattern(epithet):
    return re.compile(r"(?<!\w)" + re.escape(epithet) + r"(?!\w)", re.IGNORECASE)


def render_card_headline(headline, clubs):
    """A Rest-of-the-Card headline, with each listed epithet wrapped so the
    official club name can surface as a hint. Matching is case-insensitive and
    whole-word; an epithet the headline never uses is an error."""
    if not clubs:
        return render_inline(headline)
    spans = []                          # (start, end, club) — non-overlapping
    for entry in clubs:
        hits = list(_epithet_pattern(entry["epithet"]).finditer(headline))
        if not hits:
            raise ValueError("card headline never uses epithet {!r}: {!r}".format(
                entry["epithet"], headline))
        spans.extend((m.start(), m.end(), entry["club"]) for m in hits)
    spans.sort()
    out, pos = [], 0
    for start, end, club in spans:
        if start < pos:
            continue                    # overlapped by an earlier, longer match
        out.append(render_inline(headline[pos:start]))
        out.append('<span class="club" data-club="' + html.escape(club, quote=True)
                   + '" tabindex="0">' + render_inline(headline[start:end]) + '</span>')
        pos = end
    out.append(render_inline(headline[pos:]))
    return "".join(out)


def check_edition(data, schema):
    """Everything that must hold before an edition is written: the schema, plus
    the cross-field rule that every card epithet appears in its headline."""
    validate(data, schema)
    for g in data.get("rest_of_the_card") or []:
        render_card_headline(g["headline"], g.get("clubs"))


SITE = "https://isitspringtrainingyet.com"

_MASTHEAD_HEAD = (
    '<h1 class="masthead__title">THE MORNING HORSEHIDE HERALD</h1>'
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


def render_answer(data):
    """The line that answers the domain's question, from data already verified."""
    meta = data["meta"]
    countdown = data.get("countdown")
    if meta.get("spring_training"):
        answer = "Yes &mdash; spring training is upon us at last."
    elif meta["mode"] == "in_season":
        answer = "No &mdash; but the championship season is upon us, a finer thing still."
    elif countdown:
        answer = "Not yet &mdash; {} days until {}.".format(
            countdown["days_remaining"], render_inline(countdown["milestone"]))
    else:
        answer = "Not yet &mdash; but the stove burns bright."
    return (
        '<section class="answer"><p class="answer__line">'
        '<em>Is it spring training yet?</em> ' + answer + '</p></section>'
    )


def render_sources(sources):
    items = []
    for s in sources:
        prefix = render_inline(s["author"]) + ", " if s.get("author") else ""
        items.append(
            '<li class="sources__item">' + prefix
            + '<a href="' + html.escape(s["url"], quote=True) + '" rel="noopener">'
            + render_inline(s["title"]) + '</a> &mdash; '
            + render_inline(s["publication"]) + '</li>'
        )
    return (
        '<section class="sources">'
        '<h2 class="section__label">The Herald Acknowledges Its Debts</h2>'
        '<ul class="sources__list">' + "".join(items) + '</ul></section>'
    )


def render_edition_body(data):
    meta = data["meta"]
    parts = [render_answer(data), render_masthead(meta)]

    gotd = data.get("game_of_the_day")
    if gotd:
        parts.append(
            '<section class="game-of-the-day">'
            '<h2 class="section__label">The Game of the Day</h2>'
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
            'News Around the League</h2>' + items + '</section>'
        )

    card = data.get("rest_of_the_card") or []
    if card:
        items = "".join(
            '<div class="card__game"><h3 class="card__headline">'
            + render_card_headline(g["headline"], g.get("clubs")) + '</h3>'
            + render_body(g["body"]) + '</div>'
            for g in card
        )
        parts.append(
            '<section class="rest-of-the-card"><h2 class="section__label">'
            'The Rest of the Card</h2>' + items + '</section>'
        )

    parts.append(
        '<section class="desk-note">'
        + render_body(data["desk_note"])
        + '<p class="signoff">~ THE HERALD ~</p></section>'
    )

    sources = data.get("sources") or []
    if sources:
        parts.append(render_sources(sources))

    return "".join(parts)


def _nav_label(data):
    # Long-form dates ("the Ninth of July, Two Thousand...") shorten to the day.
    return data["meta"]["date_display"].split(",")[0]


def render_edition_nav(prev, nxt):
    if not prev and not nxt:
        return ""
    links = []
    if prev:
        links.append(
            '<a class="edition-nav__prev" href="' + edition_url(prev["meta"]["date"]) + '">'
            '&larr; ' + render_inline(_nav_label(prev)) + '</a>'
        )
    if nxt:
        links.append(
            '<a class="edition-nav__next" href="' + edition_url(nxt["meta"]["date"]) + '">'
            + render_inline(_nav_label(nxt)) + ' &rarr;</a>'
        )
    return '<nav class="edition-nav">' + "".join(links) + '</nav>'


def render_edition(data, base_template, prev=None, nxt=None):
    title = "The Morning Horsehide Herald — " + data["meta"]["date_display"]
    body = render_edition_body(data) + render_edition_nav(prev, nxt)
    return render_page(title, body, base_template)


def edition_url(date):
    year, month, day = date.split("-")
    return "/editions/{}/{}/{}.html".format(year, month, day)


def render_homepage(latest, base_template, prev=None):
    if latest is None:
        body = (
            '<header class="masthead">' + _MASTHEAD_HEAD + '</header>'
            '<section class="placeholder"><p>The presses are warming up. '
            'The first edition goes to press at dawn.</p></section>'
        )
        return render_page("The Morning Horsehide Herald", body, base_template)
    return render_edition(latest, base_template, prev=prev)


def _feed_title(data):
    gotd = data.get("game_of_the_day")
    if gotd:
        return gotd["headline"]
    return "Hot Stove Edition — " + data["meta"]["date_display"]


def render_feed(editions, limit=15):
    """Atom feed of the latest editions, full text, newest first."""
    editions = sorted(editions, key=lambda d: d["meta"]["date"], reverse=True)[:limit]
    entries = []
    for data in editions:
        date = data["meta"]["date"]
        url = SITE + edition_url(date)
        entries.append(
            "<entry>"
            "<title>" + html.escape(_feed_title(data), quote=False) + "</title>"
            '<link href="' + html.escape(url, quote=True) + '" rel="alternate"/>'
            "<id>" + url + "</id>"
            "<updated>" + date + "T11:00:00Z</updated>"
            '<content type="html">' + html.escape(render_edition_body(data), quote=False)
            + "</content>"
            "</entry>"
        )
    updated = (editions[0]["meta"]["date"] if editions else "1876-04-22") + "T11:00:00Z"
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">\n'
        "<title>The Morning Horsehide Herald</title>\n"
        "<subtitle>Every Score Set Down, No Deed Unsung</subtitle>\n"
        '<link href="' + SITE + '/" rel="alternate"/>\n'
        '<link href="' + SITE + '/feed.xml" rel="self"/>\n'
        "<id>" + SITE + "/</id>\n"
        "<updated>" + updated + "</updated>\n"
        "<author><name>The Morning Horsehide Herald</name></author>\n"
        + "\n".join(entries) + "\n</feed>\n"
    )


def build_archive_entries(editions):
    entries = []
    for data in editions:
        meta = data["meta"]
        gotd = data.get("game_of_the_day")
        entries.append({
            "date": meta["date"],
            "date_display": meta["date_display"],
            "url": edition_url(meta["date"]),
            "label": gotd["headline"] if gotd else "Hot Stove Edition",
        })
    entries.sort(key=lambda e: e["date"], reverse=True)
    return entries


_MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"]


def _month_label(date):
    year, month, _ = date.split("-")
    return _MONTH_NAMES[int(month) - 1] + " " + year


def render_archive(entries, base_template):
    months = []                          # [(label, [entry, ...])], newest first
    for e in entries:
        label = _month_label(e["date"])
        if not months or months[-1][0] != label:
            months.append((label, []))
        months[-1][1].append(e)
    sections = "".join(
        '<div class="archive__month">'
        '<h3 class="archive__month-label">' + label + '</h3>'
        '<ul class="archive__list">' + "".join(
            '<li class="archive__item"><a href="' + html.escape(e["url"], quote=True) + '">'
            + render_inline(e["date_display"]) + '</a> &mdash; '
            + render_inline(e["label"]) + '</li>'
            for e in items
        ) + '</ul></div>'
        for label, items in months
    )
    body = (
        '<header class="masthead masthead--mini">' + _MASTHEAD_HEAD + '</header>'
        '<section class="archive"><h2 class="section__label">The Archive</h2>'
        + sections + '</section>'
    )
    return render_page("The Archive — The Morning Horsehide Herald", body, base_template)


def discover_editions(root):
    files = sorted(Path(root).glob("editions/*/*/*.json"))
    return [json.loads(p.read_text(encoding="utf-8")) for p in files]


def _load_template(root):
    return (Path(root) / "templates" / "base.html").read_text(encoding="utf-8")


def _load_schema(root):
    return json.loads((Path(root) / "schema" / "edition.schema.json").read_text(encoding="utf-8"))


def render_all(root):
    root = Path(root)
    template = _load_template(root)
    schema = _load_schema(root)
    editions = discover_editions(root)
    for data in editions:               # validate everything before writing anything
        check_edition(data, schema)
    editions.sort(key=lambda d: d["meta"]["date"])
    for i, data in enumerate(editions):
        prev = editions[i - 1] if i > 0 else None
        nxt = editions[i + 1] if i + 1 < len(editions) else None
        out = root / edition_url(data["meta"]["date"]).lstrip("/")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_edition(data, template, prev, nxt), encoding="utf-8")
    latest = editions[-1] if editions else None
    penultimate = editions[-2] if len(editions) > 1 else None
    (root / "index.html").write_text(
        render_homepage(latest, template, prev=penultimate), encoding="utf-8")
    entries = build_archive_entries(editions)
    (root / "archive.html").write_text(render_archive(entries, template), encoding="utf-8")
    (root / "feed.xml").write_text(render_feed(editions), encoding="utf-8")


def render_one(root, json_path):
    root = Path(root)
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    check_edition(data, _load_schema(root))  # fail loudly on the new edition first
    render_all(root)                     # regenerate everything from disk


def inline_preview_assets(page_html, root):
    """Make a rendered page self-contained: inline the stylesheet and neutralize
    absolute nav links so it renders correctly opened directly from disk."""
    css = (Path(root) / "assets" / "herald.css").read_text(encoding="utf-8")
    page_html = page_html.replace(
        '<link rel="stylesheet" href="/assets/herald.css">',
        "<style>\n" + css + "\n</style>",
    )
    page_html = page_html.replace('href="/archive.html"', 'href="#"')
    page_html = page_html.replace('href="/feed.xml"', 'href="#"')
    page_html = page_html.replace('href="/"', 'href="#"')
    return page_html


def render_preview(root, json_path, out_path):
    """Render a single edition JSON to a self-contained HTML file at out_path.
    Validates first; writes nothing but out_path; never regenerates the site."""
    root = Path(root)
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    check_edition(data, _load_schema(root))       # fail loudly before writing anything
    page = render_edition(data, _load_template(root))
    page = inline_preview_assets(page, root)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")


def main(argv):
    root = Path(__file__).resolve().parent
    if len(argv) == 4 and argv[1] == "--preview":
        render_preview(root, argv[2], argv[3])
    elif len(argv) == 2 and argv[1] == "--all":
        render_all(root)
    elif len(argv) == 2:
        render_one(root, argv[1])
    else:
        print("usage: render.py <edition.json> | --all | --preview <edition.json> <out.html>",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
