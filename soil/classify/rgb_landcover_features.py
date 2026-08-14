"""
soil/classify/rgb_landcover_features.py
Kalli A. Hale | August 2026 | rewildingCities

The land-cover-from-RGB feature recipe (visible-band vegetation indices +
texture), factored out of segment_rf so training and application compute
pixel-for-pixel identical features. Named honestly: this is domain-specific,
it means nothing outside RGB land cover, so it is NOT pretending to be general.
The general fit/apply primitives take the table this produces; they never see
these functions.

FEATURE_NAMES is the column order, so a downstream feature table can name its
columns and the classifier can bind to them by name rather than position.
"""
import numpy as np

EPS = 1e-6

# Column order emitted by feature_stack; the single source of truth for naming.
FEATURE_NAMES = ["r", "g", "b", "exg", "vari", "gli", "texture"]


def extract_features(rgb):
    """RGB + visible-band vegetation indices (ExG, VARI, GLI) + grayscale.
    Xiao et al.'s visible-band feature set."""
    r, g, b = (rgb[..., i].astype(np.float32) for i in range(3))
    exg = 2 * g - r - b
    # VARI's denominator (g + r - b) can approach zero and blow the ratio up to
    # millions on real pixels; clip to its meaningful band, the same guard the
    # pipeline applies to NDVI. Silent spikes would otherwise skew the model.
    vari = np.clip((g - r) / (g + r - b + EPS), -1.0, 1.0)
    gli = (2 * g - r - b) / (2 * g + r + b + EPS)
    gray = rgb.mean(2).astype(np.float32)
    return exg, vari, gli, gray, r, g, b


def feature_stack(rgb, texture_window):
    """Per-pixel feature stack, shape (H, W, 7), columns == FEATURE_NAMES."""
    from scipy.ndimage import uniform_filter
    exg, vari, gli, gray, r, g, b = extract_features(rgb)
    mean = uniform_filter(gray, texture_window)
    sq = uniform_filter(gray * gray, texture_window)
    texture = np.sqrt(np.maximum(sq - mean * mean, 0))
    return np.stack([r, g, b, exg, vari, gli, texture], axis=-1)
