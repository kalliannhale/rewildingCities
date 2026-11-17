"""
tests/test_receipt_names.py ~ a receipt's name is its harvest's, forever (zip 8b)

a receipt is named <step>_<output> in its plot's one .envelopes, and a harvest
takes its receipt's name (D-318), so two runs of one plot that share a step id
and output write one receipt, the later run overwriting the earlier, and the
next canonical write moving the harvest to the other run's table. so:

  ~ no two runs of a plot write one receipt name, but the pairs named below,
    each with its reason; and a named pair that no longer collides fails too,
    so the list cannot go stale (RECNAME)
  ~ the canonical write refuses an orphan: a receipt whose run no longer
    declares the step and output that name it
  ~ the canonical write never sends a manifest dataset's cached file (D-297)

a receipt that names no run is the gate's to refuse (rule 4); these guards
leave it alone. ~
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pytest
import yaml

from canopy.aws import s3

ROOT = Path(__file__).resolve().parents[1]

# known collisions, each a reason in words, found by this test's first run
# (zip 8b): one receipt each holds whichever run went last (RUNNAMES-1).
# maine_counties predates the governance units and declares the same three
# county steps; NYC's two thermal runs share their LST steps. remove a pair
# when it is fixed, and the second test below says when one is.
_COUNTIES = "maine_counties and maine_governance_units (RUNNAMES-1)"
_NYC_LST = "nyc_thermal_landscape and nyc_park_cooling_pedestrian (RUNNAMES-1)"
KNOWN = {
    ("maine", "validate_counties_checked"): _COUNTIES,
    ("maine", "repair_counties_repaired"): _COUNTIES,
    ("maine", "dissolve_counties_dissolved"): _COUNTIES,
    ("nyc", "validate_lst_checked"): _NYC_LST,
    ("nyc", "crop_lst_cropped"): _NYC_LST,
}


def _runs(plot_dir: Path):
    for sub in ("preparations", "experiments"):
        for path in sorted((plot_dir / sub).glob("*.yml")):
            doc = yaml.safe_load(path.read_text()) or {}
            if isinstance(doc, dict) and isinstance(doc.get("steps"), list):
                yield path, doc


def _plots():
    out = []
    for manifest in sorted((ROOT / "plots").glob("**/manifest.yml")):
        if "_template" in manifest.parts:
            continue
        out.append(manifest.parent)
    return out


def receipt_names():
    """{(plot, receipt name): [run ids that write it]} across every plot."""
    names = defaultdict(list)
    for plot_dir in _plots():
        plot = plot_dir.relative_to(ROOT / "plots").as_posix()
        for _path, doc in _runs(plot_dir):
            for step in doc["steps"]:
                if not isinstance(step, dict):
                    continue
                for output in (step.get("outputs") or {}):
                    names[(plot, f"{step.get('id')}_{output}")].append(doc.get("id"))
    return names


def test_no_two_runs_of_a_plot_write_one_receipt_name():
    shared = {k: v for k, v in receipt_names().items() if len(v) > 1}
    unknown = {k: v for k, v in shared.items() if k not in KNOWN}
    assert not unknown, ("two runs write one receipt name, so one overwrites the other and a "
                         "harvest could move to the wrong table: "
                         + "; ".join(f"{p}: {n} by {', '.join(r)}" for (p, n), r in unknown.items()))


def test_a_known_collision_still_collides_or_is_removed_from_the_list():
    shared = {k for k, v in receipt_names().items() if len(v) > 1}
    stale = sorted(set(KNOWN) - shared)
    assert not stale, f"no longer collides, so remove it from KNOWN: {stale}"


def test_broadbands_standing_has_a_name_of_its_own():
    names = receipt_names()
    assert ("maine", "broadband_standardize_standings") in names
    assert ("maine", "standardize_standings") not in names


# ── the canonical write's two guards ─────────────────────────────────────
def _garden(tmp_path, *, declares=True, run_id="demo_run", dataset_cache=None):
    plot = tmp_path / "plots" / "demo"
    for sub in (".data", ".envelopes", "preparations"):
        (plot / sub).mkdir(parents=True, exist_ok=True)
    steps = [{"id": "count", "primitive": "soil/x", "outputs": {"values": "indicator_values"}}]
    if not declares:
        steps[0]["id"] = "count_renamed"
    (plot / "preparations" / f"{run_id}.yml").write_text(
        yaml.safe_dump({"id": run_id, "steps": steps}))
    if dataset_cache:
        (plot / "manifest.yml").write_text(yaml.safe_dump(
            {"datasets": {"e911_points": {"cache": {"path": dataset_cache}}}}))
    return plot


def _receipt(plot: Path, name="count_values", run="demo_run", step="count", data_name=None):
    data_name = data_name or f"{name}.parquet"
    (plot / ".data" / data_name).write_bytes(b"PAR1 bytes")
    env = {"data": {"path": f"plots/demo/preparations/../.data/{data_name}", "format": "parquet",
                    "secondary": {}},
           "metadata": {"semantic_type": "indicator_values", "lineage": {"run": run}},
           "provenance": [{"primitive": "p", "run": run, "step": step, "lineage_branch": None}],
           "warnings": []}
    (plot / ".envelopes" / f"{name}.envelope.json").write_text(json.dumps(env))
    return env


def _allow(envelope, *, plot, plot_dir):
    return {"decision": "allow", "record": {"tiers": [], "publication_steps": []}}


def test_a_receipt_its_run_still_declares_is_written(tmp_path):
    plot = _garden(tmp_path)
    _receipt(plot)
    p = s3.prepare("demo", "count_values", root=tmp_path, judge=_allow)
    assert p.harvest == "count_values"


def test_an_orphan_left_by_a_renamed_step_is_refused(tmp_path):
    plot = _garden(tmp_path, declares=False)
    _receipt(plot)
    with pytest.raises(s3.CanonicalRefusal, match="an orphan") as e:
        s3.prepare("demo", "count_values", root=tmp_path, judge=_allow)
    assert "no longer declares" in e.value.reason


def test_a_receipt_naming_a_run_the_plot_dropped_is_refused(tmp_path):
    plot = _garden(tmp_path)
    _receipt(plot, run="a_run_long_gone")
    with pytest.raises(s3.CanonicalRefusal, match="no longer declares"):
        s3.prepare("demo", "count_values", root=tmp_path, judge=_allow)


def test_a_receipt_naming_no_run_is_left_to_the_gate(tmp_path):
    plot = _garden(tmp_path)
    env = _receipt(plot)
    env["provenance"] = []
    env["metadata"].pop("lineage")
    (plot / ".envelopes" / "count_values.envelope.json").write_text(json.dumps(env))
    assert s3.prepare("demo", "count_values", root=tmp_path, judge=_allow).harvest == "count_values"


def test_a_manifest_datasets_cached_file_never_leaves(tmp_path):
    plot = _garden(tmp_path, dataset_cache="plots/demo/.data/e911.gdb.zip")
    _receipt(plot, data_name="e911.gdb.zip")
    with pytest.raises(s3.CanonicalRefusal, match="manifest dataset 'e911_points'"):
        s3.prepare("demo", "count_values", root=tmp_path, judge=_allow)


def test_a_cache_named_relative_to_the_plot_is_found_too(tmp_path):
    plot = _garden(tmp_path, dataset_cache=".data/e911.gdb.zip")
    _receipt(plot, data_name="e911.gdb.zip")
    with pytest.raises(s3.CanonicalRefusal, match="manifest dataset"):
        s3.prepare("demo", "count_values", root=tmp_path, judge=_allow)


def test_a_real_receipt_that_passes_a_fetched_source_through_never_leaves():
    """a step that only checks its input (a validate) passes the file through,
    so its receipt's data file is the fetched source itself: Maine's
    validate_counties_checked and validate_towns_checked are MEGIS's own layers.
    every such receipt in every plot is refused by the canonical write, before
    the gate is asked. skipped where a plot holds none."""
    def never(envelope, *, plot, plot_dir):
        raise AssertionError("the gate was asked about a fetched source")
    seen = 0
    for plot_dir in _plots():
        folder = plot_dir / ".envelopes"
        if not folder.is_dir():
            continue
        plot = plot_dir.relative_to(ROOT / "plots").as_posix()
        for path in sorted(folder.glob("*.envelope.json")):
            env = json.loads(path.read_text())
            given = (env.get("data") or {}).get("path")
            if not given or not (ROOT / given).resolve().is_file():
                continue
            if s3.manifest_dataset_at(ROOT, plot, (ROOT / given).resolve()) is None:
                continue
            seen += 1
            name = path.name[:-len(".envelope.json")]
            with pytest.raises(s3.CanonicalRefusal, match="passed its input through"):
                s3.prepare(plot, name, root=ROOT, judge=never)
    if not seen:
        pytest.skip("no receipt here passes a fetched source through")
