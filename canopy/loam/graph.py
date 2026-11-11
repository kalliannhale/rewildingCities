"""
canopy/loam/graph.py

graph ~ the plot's part of the weighted graph, readable in its own bed

Contract 3 keeps the graph as two tables a preparation writes, places and
edges. loam does not copy them (D-168): it holds no truth of its own, and a
copied value would leave through Loam.snapshot() without ever meeting the
gate. so loam makes two VIEWS over the files its receipts point at, and a
reader asks the bed `SELECT ... FROM places` as if the table lived there.

a view is made only when it can be trusted:

  ~ exactly one tended or gathered artifact of the type, as $loam. asks (D-163)
  ~ its receipt declares the key that names a row (KEYS-1)
  ~ the file is on disk and carries every declared key column

otherwise there is no view, and the report says why. a plot with no graph
(nyc, delton) still opens; it simply has no places to read. nothing here
writes a file, and a rebuilt bed makes the same views from the same
receipts, because there is nothing stored to drift. ~
"""

from __future__ import annotations

from pathlib import Path

CONFORMED_TIERS = ("tended", "gathered")

# the view's name in the bed, and the semantic type that fills it
GRAPH_VIEWS = {"places": "places", "edges": "place_edges"}


def _quoted(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def _reader(path: Path) -> str:
    if path.suffix == ".parquet":
        return f"read_parquet({_quoted(path)})"
    return f"read_csv_auto({_quoted(path)}, all_varchar=true)"


def plant_graph(loam, plot: str, root: str | Path) -> dict:
    """make the plot's graph views in its bed; returns, per view, whether it
    was made and from what, or why not. ~"""
    root = Path(root)
    report = {}
    for view, semantic_type in GRAPH_VIEWS.items():
        loam.con.execute(f"DROP VIEW IF EXISTS {view}")
        rows = [r for tier in CONFORMED_TIERS
                for r in loam.find(semantic_type=semantic_type, plot=plot, tier=tier)]

        def refused(why: str) -> None:
            report[view] = {"made": False, "semantic_type": semantic_type, "why": why}

        if not rows:
            refused(f"no run in plot '{plot}' has made {semantic_type}")
            continue
        if len(rows) > 1:
            receipts = sorted(Path(r["receipt_path"] or "?").name for r in rows)
            refused(f"{len(rows)} artifacts are {semantic_type}: {', '.join(receipts)}; "
                    f"which one is a choice, not a lookup (D-163)")
            continue

        row = rows[0]
        receipt = Path(row["receipt_path"] or "?").name
        key = [k for k in (row.get("id_fields") or "").split("|") if k]
        if not key:
            refused(f"{receipt} declares no key, so a row cannot be named (KEYS-1); "
                    f"rerun the preparation that made it")
            continue
        path = Path(row["data_path"])
        path = path if path.is_absolute() else root / path
        if not path.is_file():
            refused(f"{receipt} points at {row['data_path']}, which is not on disk")
            continue
        columns = [d[0] for d in loam.con.execute(
            f"SELECT * FROM {_reader(path)} LIMIT 0").description]
        missing = [k for k in key if k not in columns]
        if missing:
            refused(f"{receipt} declares the key {', '.join(key)}, but its file has no "
                    f"{', '.join(missing)}")
            continue

        loam.con.execute(f"CREATE VIEW {view} AS SELECT * FROM {_reader(path)}")
        count = loam.con.execute(f"SELECT COUNT(*) FROM {view}").fetchone()[0]
        report[view] = {"made": True, "semantic_type": semantic_type, "receipt": receipt,
                        "key": key, "rows": count}
    return report
