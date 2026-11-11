"""
canopy/wonder/session.py

session ~ opening a plot to be read

every reader needs the same five motions before it can ask anything: load
the vocabulary, open the plot's bed, plant what the manifest declares, till
what the envelopes record, and make the graph's views over what was tilled
(D-168). the CLI does this inline; an API would too, and
then they would drift in some small way that matters later.

so it lives here once. a session is not a cache and holds no truth: the bed
is re-derivable by design, and this rebuilds it from the receipts every time
rather than trusting a bed someone else may have left behind. that is
slower and it is honest, and loam was built to make it cheap. ~
"""

from __future__ import annotations

from pathlib import Path

from ..paths import project_root, loam_bed, envelopes_dir, plot_dir


class PlotNotFound(FileNotFoundError):
    """No plot of that name has been founded."""


def plot_names(root: Path | None = None) -> list[str]:
    """
    every plot this garden holds ~ a directory with a manifest is a plot.

    the closest thing to a plot registry until the grove exists: a scan,
    not a catalog. it is honest about being a scan. ~
    """
    base = (root or project_root()) / "plots"
    if not base.is_dir():
        return []
    return sorted(d.name for d in base.iterdir()
                  if d.is_dir() and not d.name.startswith((".", "_"))
                  and (d / "manifest.yml").is_file())


def open_plot(plot: str, *, root: Path | None = None, fresh: bool = True,
              directory: Path | None = None):
    """
    open a plot for reading ~ returns (vocabulary, loam, report).

    plants the manifest first, so a declared-but-unacquired holding is
    visible, then tills the receipts. the report says what happened, because
    a reader that silently refused a holding is a reader you cannot trust. ~

    `directory` names the plot's own folder outright, for a caller that
    already holds it (the orchestrator does, from its manifest), so the bed
    opened is the plot that run belongs to, wherever it sits (D-164). ~
    """
    from ..vocabulary import Vocabulary
    from ..loam.loam import Loam
    from ..loam.manifest_reader import plant_manifest
    from ..loam.envelope_reader import till_envelopes

    base = root or project_root()
    named = directory is not None
    if named:
        directory = Path(directory)
    else:
        directory = plot_dir(plot) if root is None else base / "plots" / plot
    manifest_path = directory / "manifest.yml"

    if not manifest_path.is_file():
        raise PlotNotFound(
            f"no plot at plots/{plot} ~ found one with: rewilding init {plot}")

    bed = loam_bed(plot) if root is None and not named else directory / ".loam" / "loam.duckdb"
    bed.parent.mkdir(parents=True, exist_ok=True)
    if fresh and bed.exists():
        bed.unlink()

    vocab = Vocabulary.load(base / "seeds" / "schemas")
    loam = Loam(vocab, str(bed))

    report = {"planted": 0, "planted_refused": [], "tilled": 0, "tilled_refused": []}

    # read once, by the one parser (P-01): planting and the plot's declared
    # places (D-174) both come from this reading
    from ..orchestrator.parsing import parse_manifest
    manifest = parse_manifest(manifest_path)
    planted = plant_manifest(loam, str(manifest_path), manifest=manifest)
    report["planted"] = len(planted["planted"])
    report["planted_refused"] = [{"dataset": k, "why": w} for k, w in planted["refused"]]

    receipts = envelopes_dir(plot) if root is None and not named else directory / ".envelopes"
    if receipts.is_dir():
        tilled = till_envelopes(loam, str(receipts), vocab, plot)
        report["tilled"] = len(tilled["tilled"])
        report["tilled_refused"] = [{"receipt": k, "why": w} for k, w in tilled["refused"]]

    # the plot's part of the graph, as views over the files its receipts
    # point at, never copies (D-168); a plot with no graph says so here
    from ..loam.graph import plant_graph
    report["graph"] = plant_graph(loam, plot, base, declared_places=manifest.places)

    return vocab, loam, report


def plot_display_name(plot: str, root: Path | None = None) -> str:
    """the name a community gave itself, from its manifest."""
    from ..orchestrator.parsing import parse_manifest
    base = root or project_root()
    directory = plot_dir(plot) if root is None else base / "plots" / plot
    try:
        return parse_manifest(directory / "manifest.yml").city_name
    except Exception:
        return plot
