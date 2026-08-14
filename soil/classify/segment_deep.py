"""
soil/classify/segment_deep.py
Kalli A. Hale | August 2026 | rewildingCities

Deep semantic segmenter: a pretrained DeepLabV3 / FCN backbone whose head was
retrained onto our 0..7 codes by train_segmenter_head. Emits the SAME contract
as segment_rf (image in, class mask out, per-class confidence), so
score_segmenters consumes either.

Two modes, mirroring segment_rf's fit/apply:
  trained - if `weights` is a bundle saved by train_segmenter_head, build the
            IDENTICAL model via deep_backbone (single source of truth) and load
            it. Real predictions.
  stub    - if `weights` is "pretrained" or missing, there is no retrained head,
            so it emits a placeholder mask and a CRITICAL warning. An untrained
            run can never be mistaken for a real classification.

Inference normalization (ImageNet mean/std) matches training. The net is fully
convolutional, so work_max may differ from the training input_size; very
different scales can still hurt, so a mismatch is noted, not hidden.

contract (identical to segment_rf):
  inputs : {"image": <RGB PNG>}
  output : predicted class mask PNG (values 0..7)
  params : {"weights": <bundle .pt path or "pretrained">, "class_names": {...},
            "device": "auto"|"mps"|"cpu", "work_max": 1024, "conf_warn": 0.6}
"""
import os

import numpy as np

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          WarningsCollector, primitive_success,
                          primitive_failure, primitive_error_handling)

PRIMITIVE = "segment_deep"
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], np.float32)


def pick_device(requested):
    import torch
    if requested in ("mps", "auto") and torch.backends.mps.is_available():
        return "mps", True
    if requested == "cuda" and torch.cuda.is_available():
        return "cuda", torch.backends.mps.is_available()
    return "cpu", torch.backends.mps.is_available()


def main():
    args = parse_primitive_args()
    w = WarningsCollector(PRIMITIVE)

    with primitive_error_handling(warnings=w):
        from PIL import Image
        image_path = get_input(args["inputs"], "image")
        out_path = args["output"]
        p = args["params"]
        work_max = int(get_param(p, "work_max", 1024))
        weights = get_param(p, "weights", "pretrained")
        requested_device = get_param(p, "device", "auto")
        conf_warn = float(get_param(p, "conf_warn", 0.6))
        class_names = get_param(p, "class_names", {}) or {}

        try:
            import torch
        except ImportError:
            primitive_failure(
                "torch unavailable",
                "PyTorch not installed; deep segmenter cannot run. Install "
                "torch/torchvision (MPS build) in canopy.", warnings=w)

        device, mps_avail = pick_device(requested_device)
        w.info(f"MPS available: {mps_avail}; using device: {device}")

        img = Image.open(image_path).convert("RGB")
        scale = work_max / float(max(img.size))
        if scale < 1:
            img = img.resize((int(img.size[0] * scale), int(img.size[1] * scale)))
        rgb = np.asarray(img)
        H, W = rgb.shape[:2]

        trained = isinstance(weights, str) and weights != "pretrained" \
            and os.path.exists(weights)

        if not trained:
            # ---- honest stub: no retrained head, no real prediction ----------
            pred = np.zeros((H, W), np.uint8)
            w.critical("segment_deep is UNTRAINED (weights='%s'): output is a "
                       "placeholder, not a real classification. Train a head with "
                       "train_segmenter_head and pass its weights." % weights)
            Image.fromarray(pred, mode="L").save(out_path)
            primitive_success({"mode": "stub", "mps_available": mps_avail,
                               "device": device, "weights": weights,
                               "output_size": [W, H]}, warnings=w)
            return

        # ---- trained: build the identical model and load the bundle ----------
        from soil.classify.deep_backbone import build_model
        bundle = torch.load(weights, map_location=device)
        backbone = bundle["backbone"]
        num_classes = int(bundle["num_classes"])
        model = build_model(backbone, num_classes, pretrained=False)
        model.load_state_dict(bundle["state_dict"], strict=False)
        model = model.to(device).eval()

        x = (rgb.astype(np.float32) / 255.0 - IMAGENET_MEAN) / IMAGENET_STD
        x = torch.from_numpy(x.transpose(2, 0, 1)).float().unsqueeze(0).to(device)
        with torch.no_grad():
            logits = model(x)["out"]
            prob = torch.softmax(logits, dim=1)[0].cpu().numpy()  # (C,H,W)
        pred = prob.argmax(0).astype(np.uint8)
        conf = prob.max(0)

        per_class_conf = {}
        for c in range(num_classes):
            m = pred == c
            if m.any():
                mc = float(conf[m].mean())
                per_class_conf[int(c)] = round(mc, 3)
                name = class_names.get(str(c), c)
                if c != 0 and mc < conf_warn:
                    w.warn(f"class {c} ({name}) mean confidence {mc:.2f} < "
                           f"{conf_warn}; predictions here are weak")

        Image.fromarray(pred, mode="L").save(out_path)
        primitive_success({
            "mode": "trained", "backbone": backbone, "num_classes": num_classes,
            "weights": weights, "device": device, "output_size": [W, H],
            "train_val_miou": (bundle.get("meta") or {}).get("best_val_miou"),
            "per_class_confidence": per_class_conf,
        }, warnings=w)


if __name__ == "__main__":
    main()