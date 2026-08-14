"""
ingest_stills.py
Kalli A. Hale | August 2026 | rewildingCities

SOIL ACQUISITION UTILITY (not a primitive). Container-swap plus metadata
harvest carries no interpretive content, so it emits NO Envelope and has no
semantic type. It writes a CAPTURE MANIFEST instead; that manifest is the
provenance source the downstream analytical primitives (segmentation, IPM)
pull from when THEY emit their Envelopes.

What it does, per scene folder under .data/stills/:
  1. read each HEIC (upright it via EXIF orientation, harvest device + capture
     time + orientation from EXIF)
  2. write <photographer>_<scene>_<NNN>.png, numbered per-scene in capture-time
     order
  3. append a row to capture_manifest.csv
  4. (separately, only on --delete-originals) delete the HEIC

Safe by default:
  - DRY-RUN unless --execute: prints the full plan, writes nothing.
  - Conversion and deletion are SEPARATE phases. --execute converts, verifies,
    and writes the manifest but does NOT delete. Deletion needs --delete-originals
    on top, and only proceeds for files whose PNG was written and verified. A
    conversion bug cannot take the un-reshootable originals with it.

Intended home in the repo: soil/register/ingest_stills.py (alongside acquire_*.py).

Dependency (install once in the canopy env):  pip install pillow-heif

usage:
    # 1. see the plan, change nothing:
    python ingest_stills.py plots/michigan/delton/.data/stills --photographer kalli
    # 2. actually convert + manifest (originals kept):
    python ingest_stills.py plots/michigan/delton/.data/stills --photographer kalli --execute
    # 3. once you have eyeballed the PNGs and manifest, delete the HEICs:
    python ingest_stills.py plots/michigan/delton/.data/stills --photographer kalli --execute --delete-originals
"""

import argparse
import csv
import os
import sys
from datetime import datetime


# ---- pure, testable helpers (no I/O) ------------------------------------

def scene_token(dirname):
    """Folder name -> scene token. 'landscape-forest' -> 'forest';
    'calibration' -> 'calibration'; 'landscape-open-green' -> 'open-green'."""
    return dirname[len("landscape-"):] if dirname.startswith("landscape-") else dirname


def format_name(photographer, scene, idx):
    """<photographer>_<scene>_<NNN>.png, 1-indexed, zero-padded to 3."""
    return f"{photographer}_{scene}_{idx:03d}.png"


def parse_capture_time(dto_string):
    """EXIF DateTimeOriginal 'YYYY:MM:DD HH:MM:SS' -> datetime, or None."""
    if not dto_string:
        return None
    try:
        return datetime.strptime(str(dto_string), "%Y:%m:%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def order_key(rec):
    """Sort by capture time when known, else by original filename. Filename
    order (IMG_0258, IMG_0259, ...) already tracks capture order, so it is a
    safe fallback."""
    return (rec["capture_time"] is None,
            rec["capture_time"] or datetime.min,
            rec["original_name"])


# ---- HEIC I/O (needs pillow-heif; only runs on --execute or to read EXIF) -

def load_heic(path):
    """Open a HEIC, return (upright_PIL_image, meta_dict). Reads EXIF BEFORE
    orienting so we can record the original orientation flag."""
    import pillow_heif  # imported here so --help works without the dep
    pillow_heif.register_heif_opener()
    from PIL import Image, ImageOps

    raw = Image.open(path)
    exif = raw.getexif()
    model = exif.get(272)          # Model
    orientation = exif.get(274)    # Orientation
    dto = None
    try:
        dto = exif.get_ifd(0x8769).get(36867)  # DateTimeOriginal in Exif IFD
    except Exception:
        pass

    upright = ImageOps.exif_transpose(raw)  # apply orientation, return upright
    w, h = upright.size
    meta = {
        "device": str(model) if model else "",
        "orientation": orientation if orientation is not None else "",
        "capture_time": parse_capture_time(dto),
        "capture_time_raw": str(dto) if dto else "",
        "width": w,
        "height": h,
    }
    return upright, meta


# ---- planning ------------------------------------------------------------

def collect_scene(scene_dir, scene, photographer, read_meta):
    """Build the ordered plan for one scene folder. read_meta(path)->meta lets
    tests inject a fake reader instead of touching HEIC files."""
    heics = [f for f in os.listdir(scene_dir)
             if f.lower().endswith((".heic", ".heif"))]
    records = []
    for name in heics:
        meta = read_meta(os.path.join(scene_dir, name))
        rec = {"original_name": name, "scene": scene}
        rec.update(meta)
        records.append(rec)

    records.sort(key=order_key)
    for i, rec in enumerate(records, start=1):
        rec["new_name"] = format_name(photographer, scene, i)
    return records


# ---- main ----------------------------------------------------------------

MANIFEST_FIELDS = ["new_name", "original_name", "scene", "photographer",
                   "device", "capture_time_raw", "orientation",
                   "width", "height"]


def main():
    ap = argparse.ArgumentParser(description="HEIC->PNG stills ingest (soil utility)")
    ap.add_argument("stills_dir", help="path to .data/stills")
    ap.add_argument("--photographer", required=True)
    ap.add_argument("--execute", action="store_true",
                    help="actually convert + write manifest (default: dry-run)")
    ap.add_argument("--delete-originals", action="store_true",
                    help="delete HEICs (only for verified conversions; needs --execute)")
    args = ap.parse_args()

    if not os.path.isdir(args.stills_dir):
        print(f"not a directory: {args.stills_dir}")
        sys.exit(1)

    scene_dirs = sorted(d for d in os.listdir(args.stills_dir)
                        if os.path.isdir(os.path.join(args.stills_dir, d))
                        and d != "originals")
    if not scene_dirs:
        print("no scene subfolders found")
        sys.exit(1)

    mode = "EXECUTE" if args.execute else "DRY-RUN"
    print(f"=== ingest_stills [{mode}] ===")
    print(f"stills: {args.stills_dir}\nphotographer: {args.photographer}\n")

    manifest_rows = []
    all_dims = {}  # scene -> set of (w,h), to flag inconsistent calibration frames

    for d in scene_dirs:
        scene = scene_token(d)
        scene_dir = os.path.join(args.stills_dir, d)
        try:
            records = collect_scene(scene_dir, scene, args.photographer, load_heic_meta_only)
        except ImportError:
            print("ERROR: pillow-heif not installed. Run: pip install pillow-heif")
            sys.exit(1)

        print(f"[{scene}] {len(records)} frames")
        all_dims[scene] = set()
        for rec in records:
            all_dims[scene].add((rec["width"], rec["height"]))
            print(f"    {rec['original_name']:22} -> {rec['new_name']}"
                  f"   {rec['width']}x{rec['height']}  {rec['capture_time_raw']}")

            if args.execute:
                out_png = os.path.join(scene_dir, rec["new_name"])
                upright, _ = load_heic(os.path.join(scene_dir, rec["original_name"]))
                upright.save(out_png)
                # verify: reopen and confirm dimensions
                from PIL import Image
                check = Image.open(out_png)
                if check.size != (rec["width"], rec["height"]):
                    print(f"    !! verify FAILED for {rec['new_name']}, keeping original")
                    rec["verified"] = False
                else:
                    rec["verified"] = True

            rec["photographer"] = args.photographer
            manifest_rows.append(rec)

        # calibration frames MUST share dimensions for calibrateCamera
        if len(all_dims[scene]) > 1:
            print(f"    WARNING: {scene} has mixed dimensions {all_dims[scene]}; "
                  f"if this is the calibration set, that breaks a single solve.")

    if args.execute:
        manifest_path = os.path.join(args.stills_dir, "capture_manifest.csv")
        with open(manifest_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS, extrasaction="ignore")
            w.writeheader()
            for r in manifest_rows:
                w.writerow(r)
        print(f"\nwrote manifest: {manifest_path}  ({len(manifest_rows)} rows)")

        if args.delete_originals:
            deleted = kept = 0
            for r in manifest_rows:
                if r.get("verified"):
                    os.remove(os.path.join(args.stills_dir,
                              [d for d in scene_dirs
                               if scene_token(d) == r["scene"]][0],
                              r["original_name"]))
                    deleted += 1
                else:
                    kept += 1
            print(f"deleted {deleted} verified originals; kept {kept} unverified")
        else:
            print("originals kept. Re-run with --delete-originals once you have "
                  "checked the PNGs and manifest.")
    else:
        print("\nDRY-RUN: nothing written. Add --execute to convert.")


def load_heic_meta_only(path):
    """Read just the metadata for planning (still needs pillow-heif)."""
    _, meta = load_heic(path)
    return meta


if __name__ == "__main__":
    main()