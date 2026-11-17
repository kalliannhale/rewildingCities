"""
canopy/expose/targets/base.py ~ where a plot publishes, declared by the plot

a plot names its own targets in plots/<plot>/publish/targets.yml (D-327): the
portal, the account that owns what the door makes, whether that account is an
institution's or a person's, the folder, the sharing level and the groups. no
central list exists, so a community starting a plot anywhere names its own
portal and its own owner without asking anyone (D-326).

a target's kind is how the door speaks to it. kinds sit behind one small
interface, the way providers do (canopy/providers/base.py), and register by
name. December builds one kind, arcgis_webmap; an open catalog record (DCAT or
STAC) for the open data hub is the next one named (Sprint 13).

nothing secret lives here. a password is typed at a prompt when the door
writes and is never stored (D-329). ~
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from canopy.expose.gate import SHARING_LEVELS

OWNER_KINDS = ("institutional", "personal")
SIGN_INS = ("token",)
_FIELDS = {"kind", "portal", "owner", "owner_kind", "folder", "sharing", "groups", "sign_in"}
_REQUIRED = ("kind", "portal", "owner", "owner_kind", "folder", "sharing")


class PublishRefusal(Exception):
    """the door declines, saying why and what would let it through (rule 7)."""

    def __init__(self, reason: str, would_admit: str):
        super().__init__(reason)
        self.reason = reason
        self.would_admit = would_admit


@dataclass(frozen=True)
class Target:
    id: str
    kind: str
    portal: str
    owner: str
    owner_kind: str
    folder: str
    sharing: str
    groups: tuple = ()
    sign_in: str = "token"


def targets_path(plot_dir: Path) -> Path:
    return Path(plot_dir) / "publish" / "targets.yml"


def record_path(plot_dir: Path) -> Path:
    return Path(plot_dir) / "publish" / "published.yml"


def load_targets(plot_dir: Path, kinds: dict) -> dict[str, Target]:
    """every target the plot declares, read loudly: an unknown key, a missing
    field, an unknown kind or sharing level is an error naming the target,
    never a default the door would act on."""
    path = targets_path(plot_dir)
    if not path.is_file():
        raise PublishRefusal(f"{path} does not exist, so this plot names no targets",
                             "declare one: see plots/maine/publish/targets.yml")
    doc = yaml.safe_load(path.read_text()) or {}
    declared = doc.get("targets") or {}
    if not isinstance(declared, dict) or not declared:
        raise PublishRefusal(f"{path} declares no targets", "add one under `targets:`")
    out = {}
    for tid, t in declared.items():
        t = t or {}
        where = f"target '{tid}' in {path.name}"
        unknown = sorted(set(t) - _FIELDS)
        if unknown:
            raise PublishRefusal(f"{where} has fields the door does not know: "
                                 f"{', '.join(unknown)}", f"use only {', '.join(sorted(_FIELDS))}")
        missing = [k for k in _REQUIRED if not str(t.get(k) or "").strip()]
        if missing:
            raise PublishRefusal(f"{where} is missing {', '.join(missing)}", "declare them")
        if t["kind"] not in kinds:
            raise PublishRefusal(f"{where} has kind '{t['kind']}', which no target kind "
                                 f"registers", f"use one of {', '.join(sorted(kinds))}")
        if not str(t["portal"]).startswith("https://"):
            raise PublishRefusal(f"{where}: the portal must be an https URL, got "
                                 f"'{t['portal']}'", "a sign-in is only sent over HTTPS")
        if t["owner_kind"] not in OWNER_KINDS:
            raise PublishRefusal(f"{where}: owner_kind '{t['owner_kind']}'",
                                 f"one of {', '.join(OWNER_KINDS)}")
        if t["sharing"] not in SHARING_LEVELS:
            raise PublishRefusal(f"{where}: sharing '{t['sharing']}'",
                                 f"one of {', '.join(SHARING_LEVELS)}")
        sign_in = t.get("sign_in") or "token"
        if sign_in not in SIGN_INS:
            raise PublishRefusal(f"{where}: sign_in '{sign_in}' is not built yet",
                                 "token, for now; OAuth for Enterprise portals is next (D-329)")
        groups = t.get("groups") or []
        if not isinstance(groups, list) or not all(isinstance(g, str) for g in groups):
            raise PublishRefusal(f"{where}: groups must be a list of group ids", "a list")
        out[tid] = Target(id=tid, kind=t["kind"], portal=str(t["portal"]).rstrip("/"),
                          owner=str(t["owner"]), owner_kind=t["owner_kind"],
                          folder=str(t["folder"]), sharing=t["sharing"],
                          groups=tuple(groups), sign_in=sign_in)
    return out


@dataclass
class Built:
    """what a kind would make or set, before anything is sent."""
    title: str
    snippet: str
    description: str
    tags: list
    license_info: str
    access_information: str
    data: dict                       # the item's JSON content
    layer_id: str
    url: str
    extra: dict = field(default_factory=dict)


class TargetKind(ABC):
    """how the door speaks to one kind of target. a session is whatever the
    kind returns from sign_in; the door never looks inside it."""

    name: str = ""

    @abstractmethod
    def build(self, target: Target, copy: dict) -> Built:
        """the item for this copy, from the bucket's records alone."""

    @abstractmethod
    def sign_in(self, target: Target, password: str):
        """a session, or a PublishRefusal saying why not."""

    @abstractmethod
    def whoami(self, session) -> str:
        """the account the session really is (F4)."""

    @abstractmethod
    def read(self, session, item_id: str) -> dict | None:
        """{"owner", "access", "description", "data"} for an item, None if missing."""

    @abstractmethod
    def create(self, session, target: Target, built: Built) -> str:
        """make the item in the target's folder; return its id."""

    @abstractmethod
    def update(self, session, target: Target, item_id: str, built: Built, *,
               data: dict | None) -> None:
        """set the item's description and credits, and its JSON when data is given."""

    @abstractmethod
    def share(self, session, target: Target, item_id: str) -> None:
        """share the item at the target's level and with its groups."""

    @abstractmethod
    def layer_url(self, data: dict, layer_id: str) -> str | None:
        """the URL the item's layer reads, as it stands."""

    @abstractmethod
    def moved(self, data: dict, layer_id: str, built: Built) -> dict:
        """the item's JSON with only the door's parts changed: the layer's URL and
        fields. everything a person styled (renderer, popup, basemap) is kept."""

    @abstractmethod
    def adoptable_layer(self, data: dict, url_prefix: str) -> tuple[str, str] | None:
        """(layer id, url) of a hand-made item's layer reading this harvest."""
