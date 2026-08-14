"""
soil/classify/train_segmenter_head.py
Kalli A. Hale | August 2026 | rewildingCities

Transfer-learning loop for the deep segmenter. Takes a scene-parsing corpus
(ADE20K), remaps its native labels into our 0..7 codes via the corpus crosswalk,
builds the shared deep_backbone model, trains its head (backbone frozen by
default), and saves a weights bundle that segment_deep loads. Produces REAL
weights; it is not a stub.

It cannot run without torch and the corpus on disk, so it is built to be
smoke-tested cheaply first: set max_images small and epochs 1 to prove the
mechanics (remap -> forward -> loss -> backward -> save) in seconds, then run
for real. The `weights.pt` bundle records the backbone and num_classes so
segment_deep rebuilds the identical architecture via deep_backbone.

Label remap: the corpus crosswalk is NAME-based, so a corpus index->name map is
required (ADE's label list). We compose corpus_index -> name -> our code, with
ignore/ambiguous/unknown names -> 0 (unlabeled/other). Every corpus name the
crosswalk references but the corpus lacks, and every corpus index with no
mapping, is warned, never silently dropped.

Contract: canopy/pr_io.py (three args, stdout metadata). EnvelopeBuilder wraps.
  inputs : {"images": <dir of RGB>, "labels": <dir of index masks>}
  output : weights bundle (.pt) = {backbone, num_classes, state_dict, meta}
  params : {"crosswalk": <corpus_to_seven_class.yml>,
            "corpus_label_map": <json {idx:name} or csv idx,name>,
            "backbone": "deeplabv3_resnet50", "num_classes": 8,
            "epochs": 10, "lr": 1e-3, "batch_size": 4, "input_size": 384,
            "freeze_backbone": true, "device": "auto", "val_frac": 0.1,
            "seed": 0, "max_images": null}
"""
import os
import sys
import glob
import json

import numpy as np

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          require_param, WarningsCollector, primitive_success,
                          primitive_failure, primitive_error_handling)
from soil.classify.deep_backbone import build_model, freeze_backbone

PRIMITIVE = "train_segmenter_head"
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], np.float32)


def load_label_map(path):
    """Corpus index -> name. Accepts JSON {idx:name} or CSV with idx,name."""
    if path.endswith(".json"):
        raw = json.load(open(path))
        return {int(k): str(v) for k, v in raw.items()}
    out = {}
    import csv
    with open(path) as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[0].strip().lstrip("-").isdigit():
                out[int(row[0])] = row[1].strip()
    return out


def build_lut(crosswalk_path, index_to_name, warns, num_classes):
    """Compose corpus_index -> our code (0..7). Names not mapped -> 0."""
    import yaml
    cw = yaml.safe_load(open(crosswalk_path))
    name_to_code = {}
    for key, block in (cw.get("mappings") or {}).items():
        code = int(str(key).split("_")[0])  # "4_soil" -> 4
        for src in (block.get("sources") or []):
            name_to_code[src.lower()] = code
    # ADE class names are synonym lists ("road, route"; "building, edifice"),
    # so match on ANY synonym token, not the whole string. Exact-string matching
    # would silently send road/building/sidewalk/earth/plant to 0 (other) and
    # gut most ground classes with no visible error.
    import re

    def tokens(nm):
        return [t.strip().lower() for t in re.split(r"[;,]", nm) if t.strip()]

    corpus_tokens = set()
    for nm in index_to_name.values():
        corpus_tokens.update(tokens(nm))
    missing = sorted(set(name_to_code) - corpus_tokens)
    if missing:
        warns.warn(f"crosswalk sources not present in this corpus (skipped): "
                   f"{missing[:12]}{'...' if len(missing) > 12 else ''}")
    lut = np.zeros(max(index_to_name) + 1, dtype=np.uint8)
    mapped = 0
    for idx, name in index_to_name.items():
        c = 0
        for t in tokens(name):
            if t in name_to_code:
                c = name_to_code[t]
                break
        lut[idx] = c
        mapped += (c != 0)
    warns.info(f"corpus label LUT: {mapped}/{len(index_to_name)} indices map to "
               f"ground classes 1..{num_classes - 1}; the rest -> 0 (other).")
    return lut


def main():
    w = WarningsCollector(PRIMITIVE)
    with primitive_error_handling(warnings=w):
        import torch
        import torch.nn as nn
        from torch.utils.data import Dataset, DataLoader
        from PIL import Image

        args = parse_primitive_args()
        images_dir = get_input(args["inputs"], "images")
        labels_dir = get_input(args["inputs"], "labels")
        p = args["params"]

        crosswalk = require_param(p, "crosswalk")
        label_map_path = require_param(p, "corpus_label_map")
        backbone = get_param(p, "backbone", "deeplabv3_resnet50")
        num_classes = int(get_param(p, "num_classes", 8))
        epochs = int(get_param(p, "epochs", 10))
        lr = float(get_param(p, "lr", 1e-3))
        batch_size = int(get_param(p, "batch_size", 4))
        input_size = int(get_param(p, "input_size", 384))
        do_freeze = bool(get_param(p, "freeze_backbone", True))
        unfreeze_after = get_param(p, "unfreeze_after", None)
        backbone_lr = float(get_param(p, "backbone_lr", lr * 0.1))
        device_req = get_param(p, "device", "auto")
        val_frac = float(get_param(p, "val_frac", 0.1))
        seed = int(get_param(p, "seed", 0))
        max_images = get_param(p, "max_images", None)

        # device
        if device_req in ("auto", "mps") and torch.backends.mps.is_available():
            device = "mps"
        elif device_req == "cuda" and torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"
        w.info(f"device: {device} (mps available: "
               f"{torch.backends.mps.is_available()})")

        # label remap LUT
        index_to_name = load_label_map(label_map_path)
        lut = build_lut(crosswalk, index_to_name, w, num_classes)

        # pair images with labels by stem
        imgs = sorted(glob.glob(os.path.join(images_dir, "*")))
        pairs = []
        for im in imgs:
            stem = os.path.splitext(os.path.basename(im))[0]
            for ext in (".png", ".tif", ".jpg"):
                lb = os.path.join(labels_dir, stem + ext)
                if os.path.exists(lb):
                    pairs.append((im, lb))
                    break
        rng = np.random.default_rng(seed)
        # Random diverse draw, not first-N: ADE images are numbered, so pairs[:N]
        # would bias to whatever scenes sort first. Shuffle, then cap.
        if max_images and len(pairs) > int(max_images):
            keep = sorted(rng.permutation(len(pairs))[:int(max_images)].tolist())
            pairs = [pairs[i] for i in keep]
        if len(pairs) < 2:
            primitive_failure("Too few paired samples",
                              f"found {len(pairs)} image/label pairs", w)

        order = rng.permutation(len(pairs))
        n_val = max(1, int(val_frac * len(pairs)))
        val_idx, train_idx = set(order[:n_val].tolist()), set(order[n_val:].tolist())

        class SegSet(Dataset):
            def __init__(self, idxs):
                self.items = [pairs[i] for i in sorted(idxs)]

            def __len__(self):
                return len(self.items)

            def __getitem__(self, k):
                im_p, lb_p = self.items[k]
                im = Image.open(im_p).convert("RGB").resize(
                    (input_size, input_size), Image.BILINEAR)
                lb = Image.open(lb_p).resize(
                    (input_size, input_size), Image.NEAREST)
                x = np.asarray(im, np.float32) / 255.0
                x = (x - IMAGENET_MEAN) / IMAGENET_STD
                x = torch.from_numpy(x.transpose(2, 0, 1)).float()
                y = lut[np.asarray(lb).astype(np.int64)]
                return x, torch.from_numpy(y.astype(np.int64))

        train_dl = DataLoader(SegSet(train_idx), batch_size=batch_size,
                              shuffle=True)
        val_dl = DataLoader(SegSet(val_idx), batch_size=batch_size)

        model = build_model(backbone, num_classes, pretrained=True)
        if do_freeze:
            freeze_backbone(model)
        model = model.to(device)
        params = [pp for pp in model.parameters() if pp.requires_grad]
        opt = torch.optim.Adam(params, lr=lr)
        loss_fn = nn.CrossEntropyLoss()

        def val_miou():
            model.eval()
            inter = np.zeros(num_classes); union = np.zeros(num_classes)
            with torch.no_grad():
                for x, y in val_dl:
                    pr = model(x.to(device))["out"].argmax(1).cpu().numpy()
                    yt = y.numpy()
                    for c in range(1, num_classes):  # ground classes only
                        inter[c] += np.logical_and(pr == c, yt == c).sum()
                        union[c] += np.logical_or(pr == c, yt == c).sum()
            ious = [inter[c] / union[c] for c in range(1, num_classes) if union[c]]
            return float(np.mean(ious)) if ious else 0.0

        out_path = args["output"]
        d = os.path.dirname(os.path.abspath(out_path))
        if d:
            os.makedirs(d, exist_ok=True)

        def save_bundle(state, hist, best_miou):
            torch.save({"backbone": backbone, "num_classes": num_classes,
                        "state_dict": state,
                        "meta": {"epochs": epochs, "best_val_miou": round(best_miou, 4),
                                 "history": hist, "frozen_backbone": do_freeze}},
                       out_path)

        best = -1.0
        history = []
        _HEAD = ("classifier", "aux_classifier")
        for ep in range(epochs):
            # Fine-tune: after warm-starting the head, unfreeze the backbone and
            # continue with a LOWER lr for backbone params, so pretrained
            # features get nudged, not smashed. head lr stays put.
            if do_freeze and unfreeze_after is not None and ep == int(unfreeze_after):
                for pp in model.parameters():
                    pp.requires_grad = True
                head = [pp for n, pp in model.named_parameters() if n.startswith(_HEAD)]
                back = [pp for n, pp in model.named_parameters() if not n.startswith(_HEAD)]
                opt = torch.optim.Adam([{"params": head, "lr": lr},
                                        {"params": back, "lr": backbone_lr}])
                w.info(f"epoch {ep}: unfroze backbone (head lr={lr}, "
                       f"backbone lr={backbone_lr}).")
                print(f"[epoch {ep+1}] unfroze backbone: head lr={lr}, "
                      f"backbone lr={backbone_lr}", file=sys.stderr, flush=True)
            model.train()
            running = 0.0
            for x, y in train_dl:
                opt.zero_grad()
                out = model(x.to(device))["out"]
                loss = loss_fn(out, y.to(device))
                loss.backward()
                opt.step()
                running += float(loss.item())
            miou = val_miou()
            tl = round(running / max(1, len(train_dl)), 4)
            history.append({"epoch": ep, "train_loss": tl, "val_miou": round(miou, 4)})
            improved = miou > best
            if improved:
                best = miou
                # Checkpoint to disk on every improvement, so an interrupt (or a
                # crash 11 hours in) still leaves the best weights on disk.
                save_bundle({k: v.detach().cpu() for k, v in model.state_dict().items()},
                            history, best)
            # Progress line to stderr so it streams live during a long run.
            print(f"[epoch {ep+1}/{epochs}] train_loss={tl} val_miou={miou:.4f}"
                  f"{'  <- saved best' if improved else ''}", file=sys.stderr, flush=True)

        # Safety net: guarantee a file exists even if val_miou never rose above -1.
        if best < 0:
            save_bundle({k: v.detach().cpu() for k, v in model.state_dict().items()},
                        history, 0.0)

        if best < 0.1:
            w.critical(f"best val mIoU {best:.3f} is very low; the head did not "
                       f"learn useful ground classes. Check the label remap and "
                       f"that the corpus actually contains these surfaces.")

        primitive_success({
            "primitive": PRIMITIVE, "output": out_path, "device": device,
            "backbone": backbone, "num_classes": num_classes,
            "n_train": len(train_idx), "n_val": len(val_idx),
            "epochs": epochs, "best_val_miou": round(best, 4),
            "unfreeze_after": unfreeze_after, "backbone_lr": backbone_lr,
            "history": history,
        }, w)


if __name__ == "__main__":
    main()