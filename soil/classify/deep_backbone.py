"""
soil/classify/deep_backbone.py
Kalli A. Hale | August 2026 | rewildingCities

Single source of truth for the deep segmenter's architecture, so the trainer
(train_segmenter_head) and the loader (segment_deep) build the IDENTICAL model.
If they diverged, a saved state_dict would fail to load, or load into the wrong
shapes and predict nonsense. This is the model analog of rgb_landcover_features:
one place, no drift.

Channel convention: the head outputs `num_classes` channels indexed 0..N-1,
matching our class-id codes directly. Default N=8 = codes 0..7, where 0 is
"unlabeled / other" (the corpus ignore set lands here) and 1..7 are the ground
classes. So argmax over channels yields a mask in the same 0..7 vocabulary the
class-id masks and score_segmenters already use.

torch/torchvision are imported lazily so importing this module is cheap and only
the actual build needs the deep stack (which segment_deep already requires).
"""

DEFAULT_BACKBONE = "deeplabv3_resnet50"
NUM_CLASSES = 8  # codes 0..7; 0 = unlabeled/other, 1..7 = ground classes


def build_model(backbone=DEFAULT_BACKBONE, num_classes=NUM_CLASSES,
                pretrained=True):
    """Build a torchvision segmentation model with its head resized to
    `num_classes`. Backbone weights are pretrained (transfer learning); the head
    is fresh and gets trained. Returns the nn.Module (forward -> {'out': logits})."""
    import torchvision
    from torchvision.models.segmentation.deeplabv3 import DeepLabHead
    from torchvision.models.segmentation.fcn import FCNHead

    if backbone == "deeplabv3_resnet50":
        from torchvision.models.segmentation import (
            deeplabv3_resnet50, DeepLabV3_ResNet50_Weights)
        weights = DeepLabV3_ResNet50_Weights.DEFAULT if pretrained else None
        model = deeplabv3_resnet50(weights=weights)
        model.classifier = DeepLabHead(2048, num_classes)
        if model.aux_classifier is not None:
            model.aux_classifier = FCNHead(1024, num_classes)

    elif backbone == "fcn_resnet50":
        from torchvision.models.segmentation import (
            fcn_resnet50, FCN_ResNet50_Weights)
        weights = FCN_ResNet50_Weights.DEFAULT if pretrained else None
        model = fcn_resnet50(weights=weights)
        model.classifier = FCNHead(2048, num_classes)
        if model.aux_classifier is not None:
            model.aux_classifier = FCNHead(1024, num_classes)

    else:
        raise ValueError(f"unknown backbone '{backbone}'; "
                         f"use deeplabv3_resnet50 or fcn_resnet50")
    return model


def freeze_backbone(model):
    """Freeze everything except the classifier heads, so transfer learning
    trains only the new head first (the standard warm-start)."""
    for name, param in model.named_parameters():
        param.requires_grad = name.startswith("classifier") or \
            name.startswith("aux_classifier")
    return model