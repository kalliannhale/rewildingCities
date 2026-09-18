"""

canopy/loam/loam.py

loam ~ the fertile mart the whole garden roots in

not a layer competing with soil or harvest, but the one askable bed that
indexes across every tier. rewilding plants what arrives, rewilding tills
what it works, and everything a researcher wonders is a question asked of
this ground. ♡

loam is a re-derivable catalog over durable truth (the manifest for what
is declared, the envelopes for what was tended and gathered). it holds no
truth of its own: delete the bed and rewilding plants and tills it back
from the receipts, anywhere, offline. its one law ~ it only ever holds
what a receipt already stated. it derives, it never invents.

loam is a catalog, one row per artifact, pointing at the file that holds
the values. the heavy contents stay in GeoParquet; loam records the frame
(crs, bbox) and the join grammar (id_field, id_fields, unit_key) so an explorer can
discover how two holdings relate and query them through the pointer. ~

history is read forward, never refused. a receipt may carry a retired name;
the caller resolves it through the vocabulary and passes both what was said
(semantic_type) and what it means today (canonical). loam keeps both. ~

the quiet promise (no silent choices):
  ~ spatial data (vector, raster) needs a frame (crs); a tabular result is
    frameless by nature and relates through its join keys; an arrived
    holding may not know its frame yet, and that is honest
  ~ every receipt must at least name itself; an unresolved name is kept,
    named null, and flagged, never refused
  ~ nothing reduced settles here; collapsing belongs to the harvest
  ~ a thin clump may settle, but it must say how full it is (coverage)
  ~ an unknown spot rests empty, never invented

the three tiers, in the garden tongue:
  ~ arrived  ~ bronze; a holding declared and present, planted as it comes
  ~ tended   ~ silver; a conformed artifact, tilled from its envelope
  ~ gathered ~ gold; a result raised by an experiment, tilled in as harvest

"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import duckdb

COVERAGE_FLOOR = 0.5

ARRIVED = "arrived"
TENDED = "tended"
GATHERED = "gathered"
_TIERS = (ARRIVED, TENDED, GATHERED)


def clump_name(plot: str, declared_type: str,
               content_hash: str | None = None, data_path: str | None = None) -> str:
    """

    a clump's true name, derived from what it IS (its declared name, stable
    even if we later add an alias), so the same ground re-planted converges
    instead of doubling. content hash first, the path only as fallback. ~

    """
    seed = content_hash or data_path or ""
    digest = hashlib.md5(f"{plot}:{declared_type}:{seed}".encode()).hexdigest()[:12]
    return f"{plot}:{declared_type}:{digest}"


class ConformanceError(Exception):
    """

    raised softly when a clump is not ready to take root in the loam. ♡

    """
    def __init__(self, message: str, notes: list["Note"] | None = None):
        super().__init__(message)
        self.notes = notes or []


@dataclass(frozen=True)
class Note:
    """

    a gentle word loam hands back, for the caller to fold into the real
    receipt's warnings. loam keeps no warnings of its own. ~

    """
    level: str
    message: str


@dataclass
class LoamRow:
    """

    one clump in the mart, remembering its tier, both its names (what the
    receipt said and what it means today), its frame, extent, join grammar,
    lineage, and which receipt it was read from. ~

    """
    name: str
    tier: str
    semantic_type: str | None
    semantic_type_declared: str
    spatial_ref: str | None
    plot: str
    data_path: str
    fmt: str
    crs: str | None
    native_crs: str | None
    bbox_minx: float | None
    bbox_miny: float | None
    bbox_maxx: float | None
    bbox_maxy: float | None
    id_field: str | None
    id_fields: str | None
    unit_key: str | None
    parent_ref: str | None
    conformed_by: str | None
    crosswalk_version: str | None
    coverage: float | None
    has_critical: bool
    warnings_count: int
    content_hash: str | None
    receipt_path: str | None
    created_at: float

    COLS = ("name", "tier", "semantic_type", "semantic_type_declared", "spatial_ref",
            "plot", "data_path", "fmt", "crs", "native_crs", "bbox_minx", "bbox_miny",
            "bbox_maxx", "bbox_maxy", "id_field", "id_fields", "unit_key", "parent_ref",
            "conformed_by", "crosswalk_version", "coverage", "has_critical", "warnings_count",
            "content_hash", "receipt_path", "created_at")


class Loam:
    """

    the fertile mart. rewilding `plant`s what arrives and `till`s what it
    works; `reconcile` sweeps ghosts; `find`, `overlapping`, `joinable`,
    and `trace` ask what grows, how it relates, and where it came from;
    `snapshot` lays down a parquet. one table, one law: keep only what a
    receipt stated, point at the values, forget none. ~

    """
    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS loam (
        name VARCHAR PRIMARY KEY,
        tier VARCHAR NOT NULL,
        semantic_type VARCHAR,
        semantic_type_declared VARCHAR NOT NULL,
        spatial_ref VARCHAR,
        plot VARCHAR NOT NULL,
        data_path VARCHAR NOT NULL,
        fmt VARCHAR NOT NULL,
        crs VARCHAR,
        native_crs VARCHAR,
        bbox_minx DOUBLE, bbox_miny DOUBLE, bbox_maxx DOUBLE, bbox_maxy DOUBLE,
        id_field VARCHAR,
        id_fields VARCHAR,
        unit_key VARCHAR,
        parent_ref VARCHAR,
        conformed_by VARCHAR,
        crosswalk_version VARCHAR,
        coverage DOUBLE,
        has_critical BOOLEAN NOT NULL,
        warnings_count INTEGER NOT NULL,
        content_hash VARCHAR,
        receipt_path VARCHAR,
        created_at DOUBLE NOT NULL
    );
    """

    def __init__(self, vocabulary, db_path: str, coverage_floor: float = COVERAGE_FLOOR):
        self.canonical_types = set(vocabulary.canonical)
        self._category = dict(getattr(vocabulary, "category", {}))
        self.coverage_floor = coverage_floor
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self.con = duckdb.connect(db_path)
        self.con.execute(self._SCHEMA)

    def plant(self, **f: Any) -> tuple[LoamRow, list[Note]]:
        """

        rewilding plants ~ a declared, present holding arrives at bronze. ~

        """
        return self._settle(ARRIVED, f)

    def till(self, tier: str = TENDED, **f: Any) -> tuple[LoamRow, list[Note]]:
        """

        rewilding tills ~ a conformed artifact (tended) or raised result
        (gathered) settles from its envelope. ~

        """
        if tier not in (TENDED, GATHERED):
            raise ConformanceError(f"till settles tended or gathered, not '{tier}'")
        return self._settle(tier, f)

    def _settle(self, tier: str, f: dict) -> tuple[LoamRow, list[Note]]:
        notes: list[Note] = []
        declared = f.get("semantic_type")
        sem = f.get("canonical") or declared
        crs = f.get("crs")
        sref = f.get("spatial_ref")
        coverage = f.get("coverage")

        if declared is None:
            raise ConformanceError("a receipt must at least name itself (semantic_type)", notes)

        if sem is None:
            notes.append(Note("warning",
                f"declared type '{declared}' has no canonical resolution yet; kept as history, named null"))
        elif sem not in self.canonical_types:
            notes.append(Note("warning",
                f"resolved type '{sem}' is not in the loaded vocabulary; kept, flagged"))

        # frame is category-aware: spatial data must know where on Earth it
        # sits; a tabular result is frameless and relates through join keys.
        category = self._category.get(sem)
        spatial = category in ("vector", "raster")
        if crs is None and tier != ARRIVED:
            if spatial:
                notes.append(Note("critical",
                    "no crs; a spatial clump cannot settle without a frame"))
                raise ConformanceError("loam needs an explicit crs to till spatial data", notes)
            else:
                notes.append(Note("info",
                    "tabular result ~ frameless by nature; it relates through its join keys, not a crs"))
        elif crs is None and tier == ARRIVED:
            notes.append(Note("info", "arrived without a frame yet; crs will come when tilled"))

        if f.get("crosswalk_kind") == "reducing":
            notes.append(Note("critical",
                "this clump was reduced; collapsing belongs to the harvest, not the loam"))
            raise ConformanceError("reduced data cannot rest in the loam", notes)
        if sref is None:
            notes.append(Note("warning", "exact spot unknown; it rests empty, never invented"))
        if coverage is not None and coverage < self.coverage_floor:
            notes.append(Note("warning",
                f"thin clump ~ coverage {coverage:.0%}; anything grown here will be uncertain"))

        bbox = f.get("bbox") or (None, None, None, None)
        # a composite key (id_fields, a list) is normalized to a stable,
        # order-independent string, so two tables keyed on the same set of
        # fields match in joinable() no matter the order they listed them.
        id_fields_raw = f.get("id_fields")
        # a single-element list serializes as a bare string (jsonlite drops
        # length-1 vectors to scalars), and sorting a string iterates its
        # CHARACTERS: "feature_id" became "_|a|d|e|e|f|i|r|t|u". normalize
        # to a list first, so one key and many keys are handled the same way.
        if isinstance(id_fields_raw, str):
            id_fields_raw = [id_fields_raw]
        id_fields = "|".join(sorted(id_fields_raw)) if id_fields_raw else None
        name = clump_name(f["plot"], declared, f.get("content_hash"), f.get("data_path"))
        row = LoamRow(
            name=name, tier=tier,
            semantic_type=(sem if sem in self.canonical_types else None),
            semantic_type_declared=declared,
            spatial_ref=sref, plot=f["plot"], data_path=f["data_path"], fmt=f["fmt"],
            crs=crs, native_crs=f.get("native_crs"),
            bbox_minx=bbox[0], bbox_miny=bbox[1], bbox_maxx=bbox[2], bbox_maxy=bbox[3],
            id_field=f.get("id_field"), id_fields=id_fields, unit_key=f.get("unit_key"),
            parent_ref=f.get("parent_ref"), conformed_by=f.get("conformed_by"),
            crosswalk_version=f.get("crosswalk_version"), coverage=coverage,
            has_critical=bool(f.get("upstream_has_critical", False)),
            warnings_count=int(f.get("upstream_warnings", 0)) + len(notes),
            content_hash=f.get("content_hash"), receipt_path=f.get("receipt_path"),
            created_at=time.time())

        cols = ", ".join(LoamRow.COLS)
        marks = ", ".join(["?"] * len(LoamRow.COLS))
        updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in LoamRow.COLS if c != "name")
        self.con.execute(
            f"INSERT INTO loam ({cols}) VALUES ({marks}) "
            f"ON CONFLICT (name) DO UPDATE SET {updates}",
            [getattr(row, c) for c in LoamRow.COLS])
        return row, notes

    def reconcile(self, plot: str, tier: str, living: Iterable[str]) -> int:
        """

        sweep ghosts ~ forget any clump the receipts no longer name. an
        empty living set sweeps the whole tier. returns how many were let go. ~

        """
        living = list(living)
        before = self.count(plot=plot, tier=tier)
        if not living:
            self.con.execute("DELETE FROM loam WHERE plot = ? AND tier = ?", [plot, tier])
        else:
            placeholders = ", ".join(["?"] * len(living))
            self.con.execute(
                f"DELETE FROM loam WHERE plot = ? AND tier = ? AND name NOT IN ({placeholders})",
                [plot, tier, *living])
        return before - self.count(plot=plot, tier=tier)

    def find(self, semantic_type: str | None = None, plot: str | None = None,
             tier: str | None = None, spatial_ref: str | None = None) -> list[dict]:
        """

        what grows here ~ queries by canonical semantic_type. ~

        """
        f = {"semantic_type": semantic_type, "plot": plot, "tier": tier, "spatial_ref": spatial_ref}
        keys = [k for k, v in f.items() if v is not None]
        where = (" WHERE " + " AND ".join(f"{k} = ?" for k in keys)) if keys else ""
        return self._rows(f"SELECT * FROM loam{where}", [f[k] for k in keys])

    def overlapping(self, minx: float, miny: float, maxx: float, maxy: float,
                    plot: str | None = None) -> list[dict]:
        """

        clumps whose extent overlaps a query box ~ real spatial reach. ~

        """
        clause = "bbox_minx <= ? AND bbox_maxx >= ? AND bbox_miny <= ? AND bbox_maxy >= ?"
        params = [maxx, minx, maxy, miny]
        if plot is not None:
            clause += " AND plot = ?"; params.append(plot)
        return self._rows(f"SELECT * FROM loam WHERE {clause}", params)

    def joinable(self, name: str) -> list[dict]:
        """

        which clumps could this one relate to ~ relatable when they share a
        unit_key, an id_field, a composite id_fields key, or a crs. the mart
        records the grammar; the values live in the pointed-at files. ~

        """
        r = self.con.execute("SELECT * FROM loam WHERE name = ?", [name]).fetchone()
        if not r:
            return []
        cols = [d[0] for d in self.con.description]
        me = dict(zip(cols, r))
        clauses, params = [], []
        if me.get("unit_key") is not None:
            clauses.append("unit_key = ?"); params.append(me["unit_key"])
        if me.get("id_field") is not None:
            clauses.append("id_field = ?"); params.append(me["id_field"])
        if me.get("id_fields") is not None:
            clauses.append("id_fields = ?"); params.append(me["id_fields"])
        if me.get("crs") is not None:
            clauses.append("crs = ?"); params.append(me["crs"])
        if not clauses:
            return []
        params.append(me["name"])
        return self._rows(
            f"SELECT * FROM loam WHERE ({' OR '.join(clauses)}) AND name != ?", params)

    def trace(self, name: str) -> list[str]:
        """

        follow a bloom back to its seed, clump by clump, across tiers. ~

        """
        chain, cur, guard = [], name, 0
        while cur and guard < 50:
            chain.append(cur)
            r = self.con.execute("SELECT parent_ref FROM loam WHERE name = ?", [cur]).fetchone()
            cur = r[0] if r else None
            guard += 1
        return chain

    def count(self, plot: str | None = None, tier: str | None = None) -> int:
        f = {"plot": plot, "tier": tier}
        keys = [k for k, v in f.items() if v is not None]
        where = (" WHERE " + " AND ".join(f"{k} = ?" for k in keys)) if keys else ""
        return self.con.execute(f"SELECT COUNT(*) FROM loam{where}", [f[k] for k in keys]).fetchone()[0]

    def snapshot(self, parquet_path: str) -> str:
        """

        lay down a parquet snapshot ~ the shareable, read-only bed. ~

        """
        Path(parquet_path).parent.mkdir(parents=True, exist_ok=True)
        self.con.execute(f"COPY loam TO '{parquet_path}' (FORMAT PARQUET)")
        return parquet_path

    def _rows(self, sql: str, params: list) -> list[dict]:
        cur = self.con.execute(sql, params)
        names = [d[0] for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]
