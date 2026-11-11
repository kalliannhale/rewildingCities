"""
canopy/providers/maine_legislature.py

The Maine Legislature's member lists, as a provider (D-134).

The Legislature is the record for who holds each seat. The House publishes a
real-time export of its active members (CSV); the Senate publishes a listing
of its districts as a web page, one line per district:

    District 1 (Map) - Senator Susan Bernard (R-Aroostook)

Both become one roster table with the same columns, one row per member the
record names, so build_seats reads the two chambers alike.

THREE THINGS THIS DELIBERATELY DOES NOT DO.

It does not read phone numbers. Some are members' own cell phones, published
for constituents; a public harvest would republish them in a new context
(D-138). The Phone column is never read, so it never reaches the cache.

It does not decide vacancy. A seat with no member in the roster is a fact
build_seats states, because only the places table knows which seats exist.

It does not guess at a line or a column it was not written for. A House header
that changes, or a Senate district line in a shape not seen before, is refused
rather than read: a renamed column would shift every value one place without
an error.

`as_of` is the fetch time. Neither page says which Legislature it lists or
when, so the Legislature is declared where the roster is used.
"""

from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
import csv
import io
import logging
import re

from .base import Provider, AcquisitionResult

logger = logging.getLogger("providers.maine_legislature")

COLUMNS = ["chamber", "district", "name", "party", "position", "seat_number",
           "email", "profile_url", "residence", "source", "as_of"]

# the House export's header as fetched 2026-11-11 (LEG-5). checked exactly.
HOUSE_HEADER = ["Name", "Party", "District", "County", "Seat", "Email", "Phone",
                "Residence", "City", "Zip", "Position", "Committees"]
HOUSE_NOT_READ = ["Phone", "City", "Zip", "County", "Committees"]

# the Senate listing's line, as fetched 2026-11-11 (LEG-7)
SENATE_LINE = re.compile(r"^District\s+(\d+)\s*\(Map\)\s*-\s*(.+)$")
SENATOR = re.compile(r"^Senator\s+(.+?)\s+\(([A-Za-z]+)-([^)]+)\)$")


def _blank(value):
    value = (value or "").strip()
    return value or None


def parse_house_csv(text, source, as_of):
    """the House export as roster rows. refuses a header it was not written for."""
    reader = csv.reader(io.StringIO(text))
    header = [h.strip() for h in next(reader, [])]
    if header != HOUSE_HEADER:
        raise ValueError(f"House export header changed: expected {HOUSE_HEADER}, got {header}")
    rows = []
    for record in reader:
        if not any(cell.strip() for cell in record):
            continue
        r = dict(zip(header, record))
        rows.append({
            "chamber": "house", "district": _blank(r["District"]), "name": _blank(r["Name"]),
            "party": _blank(r["Party"]), "position": _blank(r["Position"]),
            "seat_number": _blank(r["Seat"]), "email": _blank(r["Email"]),
            "profile_url": None, "residence": _blank(r["Residence"]),
            "source": source, "as_of": as_of})
    return rows


class _Page(HTMLParser):
    """the page's text, broken into lines at block tags, and every link."""

    BREAKS = {"p", "li", "br", "div", "tr", "td", "h1", "h2", "h3", "h4", "ul", "ol"}

    def __init__(self):
        super().__init__()
        self.pieces, self.links = [], []
        self._href, self._link_text = None, []

    def handle_starttag(self, tag, attrs):
        if tag in self.BREAKS:
            self.pieces.append("\n")
        if tag == "a":
            self._href, self._link_text = dict(attrs).get("href"), []

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((" ".join("".join(self._link_text).split()), self._href))
            self._href = None
        if tag in self.BREAKS:
            self.pieces.append("\n")

    def handle_data(self, data):
        self.pieces.append(data)
        if self._href is not None:
            self._link_text.append(data)

    def lines(self):
        return [" ".join(line.split()) for line in "".join(self.pieces).split("\n")]


def parse_senate_html(html, source, as_of):
    """the Senate's district listing as roster rows.

    returns (rows, vacant_lines). a district line naming no senator but saying
    vacant is counted and given no row; any other line shape is refused."""
    page = _Page()
    page.feed(html)
    rows, vacant = [], 0
    for line in page.lines():
        m = SENATE_LINE.match(line)
        if not m:
            continue
        district, rest = m.group(1), m.group(2).strip()
        s = SENATOR.match(rest)
        if s:
            name, party = s.group(1).strip(), s.group(2)
            link = next((href for text, href in page.links
                         if name in text and href), None)
            rows.append({
                "chamber": "senate", "district": district, "name": name, "party": party,
                "position": None, "seat_number": None, "email": None,
                "profile_url": urljoin(source, link) if link else None,
                "residence": None, "source": source, "as_of": as_of})
        elif rest.lower().startswith("vacant"):
            vacant += 1
        else:
            raise ValueError(f"Senate listing line in an unknown shape: {line!r}")
    if not rows and not vacant:
        raise ValueError("Senate listing has no district lines; the page changed shape")
    return rows, vacant


def write_rows(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        import pandas as pd
        pd.DataFrame(rows, columns=COLUMNS).to_parquet(path, index=False)
    else:
        with open(path, "w", newline="") as f:
            out = csv.DictWriter(f, fieldnames=COLUMNS)
            out.writeheader()
            out.writerows(rows)


class MaineLegislatureProvider(Provider):
    """source: {type: api, provider: maine_legislature, chamber: house|senate, url: ...}"""

    @property
    def name(self) -> str:
        return "Maine Legislature"

    def can_handle(self, source_config: dict) -> bool:
        return (source_config.get("type") == "api"
                and source_config.get("provider") == "maine_legislature")

    def acquire(self, source_config, cache_path: Path, dataset_name: str, **kwargs):
        import requests

        chamber = source_config.get("chamber")
        url = source_config.get("url")
        if chamber not in ("house", "senate") or not url:
            return AcquisitionResult(dataset_name=dataset_name, success=False,
                                     message="maine_legislature needs chamber (house or senate) and url")
        as_of = datetime.now(timezone.utc).isoformat()
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        try:
            if chamber == "house":
                rows, vacant, not_read = parse_house_csv(resp.text, url, as_of), None, HOUSE_NOT_READ
            else:
                (rows, vacant), not_read = parse_senate_html(resp.text, url, as_of), []
        except ValueError as e:
            return AcquisitionResult(dataset_name=dataset_name, success=False,
                                     message=f"{chamber} record refused: {e}")
        write_rows(rows, cache_path)
        size = Path(cache_path).stat().st_size
        provenance = {
            "provider": "maine_legislature", "chamber": chamber, "url": url,
            "n_members": len(rows), "vacant_lines": vacant, "fields_not_read": not_read,
            "format": Path(cache_path).suffix.lstrip("."), "fetched_at": as_of}
        return AcquisitionResult(
            dataset_name=dataset_name, success=True, path=str(cache_path), size_bytes=size,
            message=f"{len(rows)} {chamber} member(s) from the Maine Legislature, as of {as_of}",
            provenance=provenance)
