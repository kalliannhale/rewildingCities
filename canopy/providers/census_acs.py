"""
canopy/providers/census_acs.py

The American Community Survey, as a provider.

The ACS is the single largest source behind county-level civic indicators ~
broadband, language spoken at home, educational attainment, rent burden,
vehicle access, disconnected youth, neighbourhood poverty, income inequality.
The Civic Information Index draws roughly a third of its twenty-seven
indicators from here. One provider, many indicators, and it works for any
county in the United States rather than only the one plot we happen to be
looking at.

THREE THINGS THIS DELIBERATELY DOES NOT DO.

It does not compute rates. The ACS publishes counts, and a percentage is a
derivation: which numerator, which denominator, what happens when the
denominator is zero. Those are analytical choices that deserve their own
envelope, so the provider fetches B28002_004E and B28002_001E and a primitive
downstream decides what to do with them. One acquisition can then serve
several derivations, and the arithmetic is auditable rather than buried in a
fetch.

It does not guess the geography. `geography: county, within: {state: "23"}`
returns Maine's sixteen; `geography: tract, within: {state: "23", county:
"005"}` returns Cumberland's tracts. The same indicator at a different grain
is a different measurement, and a plot says which one it wants.

It does not silently pass through the Census's annotation values. The ACS
encodes "estimate not computable", "not applicable" and several other states
as large negative numbers ~ -666666666 and friends. Read naively these look
like data and will quietly wreck an average. They are converted to empty and
reported by count, because an unknown should rest empty rather than arrive
disguised as a very small number.

WHICH VARIABLES. A source may name `indicators: [...]` from the indicator
registry (seeds/indicators/) instead of raw codes, and the provider asks the
registry what each needs, margins of error included. The registry is then the
single place a variable code is written, so a manifest and a registry can
never quietly disagree about what broadband means. Raw `variables` are still
accepted alongside, and the two are unioned.

ON FORMAT. Written as parquet when the cache path says .parquet, because the
GEOID is a zero-padded string and CSV cannot say so: read back, '01001'
(Autauga County, Alabama) becomes the integer 1001 and every join to TIGER
fails silently. Maine's '23' survives by luck. CSV is still written when the
path asks for it.

ON VINTAGE. For a five-year release, `year: 2024` means the 2020-2024
estimates, and the window is recorded rather than inferred. This matters for
comparability: the 2026 Civic Information Index used 2020-2024, the 2024
edition used 2018-2022, and an index recomputed next year against 2021-2025
is no longer comparing like with like. The window belongs in the record.
"""

from datetime import datetime, timezone
from pathlib import Path
import csv
import logging
import os

from .base import Provider, AcquisitionResult

logger = logging.getLogger("providers.census_acs")

API_ROOT = "https://api.census.gov/data"

# The Census API documents a limit of 50 variables per request. Past it, the
# request is refused rather than split: splitting means rejoining on GEOID,
# which is worth building when an acquisition actually needs it.
MAX_GET = 50

# canopy/providers/census_acs.py -> repo root. Resolved from this file, not
# the working directory, so a server finds the registry as reliably as a CLI.
INDICATORS_DIR = Path(__file__).resolve().parents[2] / "seeds" / "indicators"

# The Census encodes non-values as large negative integers. Each has a distinct
# meaning and all of them are "this is not a number you may average".
JAM_VALUES = {
    "-999999999": "estimate not available",
    "-888888888": "not applicable",
    "-666666666": "estimate not computable (too few sample observations)",
    "-555555555": "estimate controlled; a margin of error is not appropriate",
    "-333333333": "not applicable",
    "-222222222": "estimate not available",
}

# ACS-6: the annotations arrive in more than one spelling. a count variable
# returns "-666666666"; a median or a ratio returns "-666666666.0". matching
# the text exactly caught the first and missed the second, so Maine towns
# without renters carried a rent burden of minus 666 million and the town
# map was colored by it. an annotation is a NUMBER with a meaning, so it is matched
# as a number, whatever decimals it is written with.
_JAM_BY_NUMBER = {int(k): k for k in JAM_VALUES}


def jam_key(token: str) -> str | None:
    """The canonical annotation a raw Census token stands for, or None when it
    is an ordinary value (or not a number at all, which is counted elsewhere).
    "-666666666", "-666666666.0" and "-666666666.00" are the same annotation."""
    try:
        value = float(token)
    except (TypeError, ValueError):
        return None
    if value != value or not value.is_integer():
        return None
    return _JAM_BY_NUMBER.get(int(value))


# How many digits each level of the hierarchy contributes to a GEOID, and
# which parent levels it must be nested within. A GEOID is built by
# concatenation, which is what makes it joinable to TIGER without a lookup.
GEOGRAPHY = {
    "state":             {"parents": [],                    "width": {"state": 2}},
    "county":            {"parents": ["state"],             "width": {"state": 2, "county": 3}},
    "county subdivision": {"parents": ["state", "county"],  "width": {"state": 2, "county": 3,
                                                                      "county subdivision": 5}},
    "place":             {"parents": ["state"],             "width": {"state": 2, "place": 5}},
    "tract":             {"parents": ["state", "county"],   "width": {"state": 2, "county": 3,
                                                                      "tract": 6}},
    "block group":       {"parents": ["state", "county", "tract"],
                          "width": {"state": 2, "county": 3, "tract": 6, "block group": 1}},
}


class CensusACSProvider(Provider):
    """Acquires raw American Community Survey variables for a geography."""

    @property
    def name(self) -> str:
        return "US Census ACS"

    def can_handle(self, source_config: dict) -> bool:
        return (
            source_config.get("type") == "api"
            and source_config.get("provider") == "census_acs"
        )

    # ── vintage ────────────────────────────────────────────────────────────
    @staticmethod
    def vintage_window(dataset: str, year: int) -> str:
        """
        The period a release actually covers, spelled out.

        A five-year release labelled 2024 covers 2020-2024. Recording "2024"
        alone invites a later reader to compare it against a different window
        and believe they are comparing like with like.
        """
        if dataset.endswith("acs5"):
            return f"{year - 4}-{year} (5-year estimates)"
        if dataset.endswith("acs3"):
            return f"{year - 2}-{year} (3-year estimates)"
        if dataset.endswith("acs1"):
            return f"{year} (1-year estimates)"
        return str(year)

    # ── request ────────────────────────────────────────────────────────────
    def build_request(self, source_config: dict) -> tuple[str, dict, list[str]]:
        """Return (url, params, problems). Problems are fatal; the caller reports them."""
        problems: list[str] = []

        dataset = source_config.get("dataset", "acs/acs5")
        year = source_config.get("year")
        geography = (source_config.get("geography") or "").strip()
        within = source_config.get("within") or {}
        variables, var_problems = self.resolve_variables(source_config)
        problems.extend(var_problems)

        if not year:
            problems.append("no `year` declared; an ACS release has no default vintage")
        if not variables and not var_problems:
            problems.append("no `indicators` or `variables` declared; name what to fetch")
        if geography not in GEOGRAPHY:
            problems.append(
                f"geography {geography!r} is not one this provider builds a GEOID for. "
                f"Known: {', '.join(sorted(GEOGRAPHY))}")

        if geography in GEOGRAPHY:
            missing = [p for p in GEOGRAPHY[geography]["parents"] if p not in within]
            if missing:
                problems.append(
                    f"geography {geography!r} must be nested within "
                    f"{', '.join(missing)}; declare them under `within`")

        if problems:
            return "", {}, problems

        # NAME always comes along: a human-readable label beside a code is the
        # difference between a table someone can check and one they must trust.
        get = ["NAME"] + [v for v in variables if v != "NAME"]
        if len(get) > MAX_GET:
            return "", {}, [
                f"{len(get)} variables requested (NAME included); the Census API "
                f"accepts {MAX_GET} per request. Split this acquisition by indicator "
                f"for now; a provider that splits and rejoins on GEOID is a "
                f"recorded follow-up, not something to improvise here."]

        params = {
            "get": ",".join(get),
            "for": f"{geography}:*",
        }
        if within:
            params["in"] = " ".join(f"{k}:{v}" for k, v in within.items())

        key = source_config.get("api_key") or os.environ.get("CENSUS_API_KEY")
        if key:
            params["key"] = key

        return f"{API_ROOT}/{year}/{dataset}", params, []

    # ── variables ──────────────────────────────────────────────────────────
    @staticmethod
    def resolve_variables(source_config: dict) -> tuple[list[str], list[str]]:
        """
        Every variable this acquisition must fetch, and any problems.

        Indicators are resolved through the registry, which adds each
        estimate's margin-of-error sibling when the indicator declares
        acs_moe. An indicator declared for a different provider or dataset is
        refused: a 1-year estimate is not the 5-year estimate it was defined
        against, even when the variable codes are identical.
        """
        problems: list[str] = []
        ordered: list[str] = []

        def add(v: str) -> None:
            if v not in ordered:
                ordered.append(v)

        names = source_config.get("indicators") or []
        if isinstance(names, str):
            names = [names]
        if names:
            from canopy.indicators import IndicatorRegistry
            try:
                registry = IndicatorRegistry.load(INDICATORS_DIR)
            except (FileNotFoundError, ValueError) as e:
                return [], [f"the indicator registry could not be loaded: {e}"]
            dataset = source_config.get("dataset", "acs/acs5")
            for name in names:
                try:
                    ind = registry.get(name)
                except KeyError as e:
                    problems.append(e.args[0] if e.args else str(e))
                    continue
                if ind.source.get("provider") != "census_acs":
                    problems.append(
                        f"indicator '{name}' is declared for provider "
                        f"'{ind.source.get('provider')}', not census_acs")
                    continue
                declared = ind.source.get("dataset")
                if declared and declared != dataset:
                    problems.append(
                        f"indicator '{name}' is defined against {declared}; this "
                        f"acquisition fetches {dataset}. same codes, different estimate.")
                    continue
                for v in ind.acquisition_variables():
                    add(v)

        raw = source_config.get("variables") or []
        if isinstance(raw, str):
            raw = [raw]
        for v in raw:
            add(v)

        return ordered, problems

    @staticmethod
    def _public_request(url: str, params: dict) -> dict:
        """The request as it may be recorded: never the key."""
        return {"url": url,
                "params": {k: v for k, v in params.items() if k != "key"}}

    # ── acquire ────────────────────────────────────────────────────────────
    def acquire(self, source_config, cache_path: Path, dataset_name: str, **kwargs):
        import requests

        url, params, problems = self.build_request(source_config)
        if problems:
            return AcquisitionResult(
                dataset_name=dataset_name, success=False,
                message="ACS source is underspecified:\n  - " + "\n  - ".join(problems))

        dataset = source_config.get("dataset", "acs/acs5")
        year = int(source_config.get("year"))
        geography = source_config.get("geography")
        window = self.vintage_window(dataset, year)
        notes: list[str] = []
        warnings: list[dict] = []

        if "key" not in params:
            notes.append("no API key (set CENSUS_API_KEY); the Census rate-limits "
                         "anonymous requests and may refuse a large one")

        try:
            logger.info(f"  Census ACS: {url} [{geography}]")
            resp = requests.get(url, params=params, timeout=180)
        except Exception as e:
            return AcquisitionResult(
                dataset_name=dataset_name, success=False,
                message=f"Census ACS request failed: {e}")

        # The Census answers a keyless request with HTTP 200 and an HTML page,
        # so a naive json() call fails with a parse error that says nothing
        # about the actual problem. Detect it and name the remedy, because a
        # credential the operator can obtain in two minutes is a different
        # situation from one somebody has to grant them.
        if "missing_key" in resp.url or "Missing Key" in resp.text[:400]:
            return AcquisitionResult(
                dataset_name=dataset_name, success=False,
                requires_auth=True,
                auth_instructions=(
                    "The Census Bureau requires an API key for this endpoint. Keys are "
                    "free, issued immediately, and self-service:\n"
                    "  https://api.census.gov/data/key_signup.html\n"
                    "Then either export CENSUS_API_KEY in the environment, or declare "
                    "`api_key` on the source."),
                message="The Census API requires a key, which has not been supplied.")

        if resp.status_code == 404:
            return AcquisitionResult(
                dataset_name=dataset_name, success=False,
                message=(f"The Census returned 404 for {dataset} {year}. Either the "
                         f"release is not published yet, or a variable code does not "
                         f"exist in this vintage. Variable codes change between "
                         f"releases; check {API_ROOT}/{year}/{dataset}/variables.html"))

        try:
            resp.raise_for_status()
        except Exception as e:
            return AcquisitionResult(
                dataset_name=dataset_name, success=False,
                message=f"Census ACS returned {resp.status_code}: {resp.text[:300]}")

        # A non-JSON body here means the request was malformed in a way the
        # Census answers in prose. Report the prose rather than a parse error.
        try:
            rows = resp.json()
        except ValueError:
            return AcquisitionResult(
                dataset_name=dataset_name, success=False,
                message=(f"The Census returned a non-JSON response "
                         f"(content-type {resp.headers.get('content-type')}). This is "
                         f"usually an unknown variable code or a malformed geography.\n"
                         f"  body begins: {resp.text[:300]}"))

        if not rows or len(rows) < 2:
            return AcquisitionResult(
                dataset_name=dataset_name, success=False,
                message=(f"The Census returned no rows for {geography} in "
                         f"{source_config.get('within')}. The geography may be empty or "
                         f"the nesting may be wrong."))

        header, body = rows[0], rows[1:]
        index = {name: i for i, name in enumerate(header)}

        # ── GEOID, by concatenation ────────────────────────────────────────
        # The ACS returns the hierarchy as separate columns. Joined in order
        # and zero-padded, they ARE the Census GEOID, which is the same key a
        # TIGER boundary carries. Building it here means the spatial join is
        # derivable rather than a name match ~ '23' + '005' is Cumberland
        # County, in Maine's own GIS and in the Census, without a crosswalk.
        widths = GEOGRAPHY[geography]["width"]
        parts = [p for p in GEOGRAPHY[geography]["parents"]] + [geography]
        missing_parts = [p for p in parts if p not in index]
        if missing_parts:
            warnings.append({
                "level": "warning", "primitive": "census_acs",
                "message": (f"The response is missing hierarchy column(s) "
                            f"{', '.join(missing_parts)}, so no GEOID could be built. "
                            f"The data is written without a join key.")})

        def geoid_for(row) -> str:
            if missing_parts:
                return ""
            return "".join(str(row[index[p]]).zfill(widths[p]) for p in parts)

        # ── requested vs returned ─────────────────────────────────────────
        variables = [v for v in params["get"].split(",") if v != "NAME"]
        var_cols = [v for v in variables if v in index]
        not_returned = [v for v in variables if v not in index]
        if not_returned:
            warnings.append({
                "level": "warning", "primitive": "census_acs",
                "message": (f"{len(not_returned)} requested variable(s) are absent from "
                            f"the response and are not in the file: "
                            f"{', '.join(not_returned)}. Anything derived from them "
                            f"cannot be computed.")})

        # ── jam values ─────────────────────────────────────────────────────

        jam_counts: dict[str, int] = {}
        cleaned: list[dict] = []

        for row in body:
            out = {"GEOID": geoid_for(row), "NAME": row[index["NAME"]] if "NAME" in index else ""}
            for p in parts:
                if p in index:
                    out[p.replace(" ", "_")] = str(row[index[p]]).zfill(widths[p])
            for v in var_cols:
                raw = row[index[v]]
                token = str(raw).strip() if raw is not None else ""
                annotation = jam_key(token)
                if annotation is not None:
                    jam_counts[annotation] = jam_counts.get(annotation, 0) + 1
                    out[v] = ""          # rests empty; never a very negative number
                else:
                    out[v] = token
            cleaned.append(out)

        for token, count in sorted(jam_counts.items()):
            warnings.append({
                "level": "warning", "primitive": "census_acs",
                "message": (f"{count} value(s) were the Census annotation {token} "
                            f"({JAM_VALUES[token]}) and rest empty rather than being "
                            f"read as a number. An average computed over these without "
                            f"removing them would be badly wrong.")})

        # ── write ──────────────────────────────────────────────────────────
        id_cols = ["GEOID", "NAME"] + [p.replace(" ", "_") for p in parts if p in index]
        fieldnames = id_cols + var_cols
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        ext = cache_path.suffix.lower()

        unparseable = 0
        if ext == ".parquet":
            import pandas as pd

            def number(token: str):
                nonlocal unparseable
                if token == "":
                    return None
                try:
                    return float(token)
                except ValueError:
                    unparseable += 1
                    return None

            frame = pd.DataFrame(cleaned, columns=fieldnames)
            for c in id_cols:
                frame[c] = frame[c].astype("string")
            for v in var_cols:
                frame[v] = pd.Series([number(t) for t in frame[v]], dtype="Float64")
            frame.to_parquet(cache_path, index=False)
        elif ext == ".csv":
            with open(cache_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(cleaned)
        else:
            return AcquisitionResult(
                dataset_name=dataset_name, success=False,
                message=(f"cache path {cache_path.name} has extension '{ext}'; this "
                         f"provider writes .parquet or .csv, by declaration."))

        if unparseable:
            warnings.append({
                "level": "warning", "primitive": "census_acs",
                "message": (f"{unparseable} value(s) were neither numbers nor known "
                            f"Census annotations and rest empty. Inspect the raw "
                            f"response before trusting any derivation over them.")})

        size = cache_path.stat().st_size
        notes.insert(0, f"{len(cleaned)} {geography}(s)")
        notes.insert(1, f"vintage {window}")
        notes.insert(2, f"{len(var_cols)} variable(s)")
        if jam_counts:
            notes.append(f"{sum(jam_counts.values())} annotated non-value(s) emptied")

        provenance = {
            "provider": "census_acs",
            "dataset": dataset,
            "year": year,
            "vintage_window": window,
            "geography": geography,
            "within": dict(source_config.get("within") or {}),
            "indicators": list(source_config.get("indicators") or []),
            "variables_requested": variables,
            "variables_returned": var_cols,
            "variables_not_returned": not_returned,
            "n_units": len(cleaned),
            "annotations_emptied": {t: c for t, c in sorted(jam_counts.items())},
            "unparseable_emptied": unparseable,
            "request": self._public_request(url, params),
            "api_key_used": "key" in params,
            "format": ext.lstrip("."),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        return AcquisitionResult(
            dataset_name=dataset_name,
            success=True,
            path=str(cache_path),
            size_bytes=size,
            message="Fetched from the Census ACS ~ " + "; ".join(notes),
            warnings=warnings,
            provenance=provenance,
        )

    # ── discover ───────────────────────────────────────────────────────────
    def discover(self, bbox, semantic_types=None, **kwargs):
        """
        Not implemented, deliberately.

        Discovery here would mean turning a bounding box into the FIPS codes it
        covers, which needs a spatial lookup this provider does not have. A
        provider that guessed would return confident wrong geographies, so it
        returns nothing and the caller reports the gap honestly.
        """
        return []