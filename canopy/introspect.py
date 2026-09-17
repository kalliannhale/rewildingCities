"""
canopy/introspect.py

introspect ~ honest sensing of the environment this run is actually in

one job: tell the truth about what THIS machine can do right now, so the
resolution layer can offer a person real options instead of pretending. it
indexes nothing (that is loam) and acquires nothing (that is the engine). it
only senses: is there disk, is there network, are there credentials, is a
provider reachable. every answer is a fact about the here-and-now, with an
honest False where it cannot know rather than a guess. ♡

pure standard library, no external dependency, so it runs the same on a
laptop, in CI, and in a cloud job ~ and a module install and a cloud
deployment get different, truthful answers to the same question. ~
"""

from __future__ import annotations

import os
import shutil
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


# --- disk --------------------------------------------------------------------

@dataclass(frozen=True)
class DiskHeadroom:
    """free space where an artifact would land, in bytes and as a fraction. ~"""
    path: str
    total_bytes: int
    free_bytes: int

    @property
    def free_ratio(self) -> float:
        return (self.free_bytes / self.total_bytes) if self.total_bytes else 0.0

    @property
    def free_gib(self) -> float:
        return self.free_bytes / (1024 ** 3)


def disk_headroom(path: str | os.PathLike = ".") -> DiskHeadroom:
    """how much room is left where this path lives. if the path does not exist
    yet, sense the nearest existing parent, so a not-yet-created plot dir still
    gets a truthful answer. ~"""
    p = Path(path).resolve()
    while not p.exists() and p != p.parent:
        p = p.parent
    usage = shutil.disk_usage(str(p))
    return DiskHeadroom(path=str(p), total_bytes=usage.total, free_bytes=usage.free)


# --- network -----------------------------------------------------------------

def is_online(timeout: float = 1.5) -> bool:
    """can this machine reach the network right now ~ a real request to a
    connectivity-check endpoint (Google's generate_204) that answers with an
    empty HTTP 204. requiring the 204 is what makes this honest: a captive
    portal or proxy that intercepts with a 200-and-a-login-page reads as
    offline, which for real traffic it effectively is. no bytes leave beyond
    the check itself. ~"""
    import urllib.request
    req = urllib.request.Request("http://www.gstatic.com/generate_204", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 204
    except Exception:
        return False


# --- credentials -------------------------------------------------------------

# where each kind of credential honestly lives: environment variables (any
# present counts) and/or files (any existing counts). best-effort per provider,
# named not guessed; an unknown kind returns False. extend as providers are
# added. NOTE: arcgis also supports stored profiles; env is the portable,
# unambiguous signal, so that is what we assert on until visuals needs more.
_CREDENTIALS = {
    "aws": {
        "env": ("AWS_ACCESS_KEY_ID",),
        "files": ("~/.aws/credentials",),
    },
    "earthengine": {
        "env": ("EARTHENGINE_TOKEN",),
        "files": ("~/.config/earthengine/credentials",),
    },
    "arcgis": {
        "env": ("ARCGIS_API_KEY", "ARCGIS_USERNAME"),
        "files": (),
    },
}


def has_credentials(kind: str) -> bool:
    """are credentials of this kind present on this machine ~ checks the env
    vars and files where that kind actually lives. an unknown kind is False. ~"""
    spec = _CREDENTIALS.get(kind)
    if spec is None:
        return False
    if any(os.environ.get(name) for name in spec.get("env", ())):
        return True
    if any(Path(f).expanduser().exists() for f in spec.get("files", ())):
        return True
    return False


# --- provider reachability ---------------------------------------------------

_URL_KEYS = ("url", "endpoint", "href", "base_url", "host", "api")


def _host_of(source: dict) -> str | None:
    """pull a hostname out of a source block if it carries one. ~"""
    for key in _URL_KEYS:
        val = source.get(key)
        if not isinstance(val, str) or not val:
            continue
        ref = val if "://" in val else "//" + val
        host = urlparse(ref).hostname
        if host:
            return host
    return None


def provider_reachable(source: dict, timeout: float = 2.0) -> bool:
    """can this run reach the provider this source points at ~ if the source
    names an endpoint, try that host; if it names none, fall back to general
    connectivity (is_online) and return that. an honest here-and-now read, not
    a promise the acquire will succeed. ~"""
    if not isinstance(source, dict):
        return is_online(timeout=timeout)
    host = _host_of(source)
    if host is None:
        return is_online(timeout=timeout)
    for port in (443, 80):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            continue
    return False


# --- a quick honest snapshot -------------------------------------------------

@dataclass(frozen=True)
class Environment:
    """a here-and-now read of what this machine can do. ~"""
    online: bool
    disk: DiskHeadroom
    credentials: dict  # kind -> bool, for the kinds asked about


def sense(path: str | os.PathLike = ".",
          credential_kinds: tuple[str, ...] = ()) -> Environment:
    """one honest snapshot ~ online?, room where work would land, and which of
    the asked-about credential kinds are present. senses only; changes
    nothing. ~"""
    return Environment(
        online=is_online(),
        disk=disk_headroom(path),
        credentials={k: has_credentials(k) for k in credential_kinds},
    )
