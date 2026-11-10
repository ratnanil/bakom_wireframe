#!/usr/bin/env python3
"""
Synthetic bivariate raster: Accessibility × Availability
Extent: ll=(47.361924, 8.610190), ur=(47.412530, 8.712478) [WGS84]

Accessibility: fBm Perlin noise, large scale  (far=0 → near=1)
Availability:  fBm Perlin noise, finer scale  (low=0 → high=1)

Outputs
-------
bivariate.tif     RGBA GeoTIFF  — georeferenced visualization
bivariate_raw.tif 2-band float  — band 1 = accessibility, band 2 = availability
legend.png        3×3 color matrix legend
"""

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.enums import ColorInterp
from PIL import Image
from noise import pnoise2
from config import LON_MIN, LAT_MIN, LON_MAX, LAT_MAX, RASTER_RGBA, RASTER_RAW, LEGEND_OUT

# Mercator aspect ratio: width/height when displayed in EPSG:3857.
# At lat ~47.4°, 1° lon < 1° lat in metric, so ROWS < naive value.
_merc_y = lambda lat: np.log(np.tan(np.pi/4 + np.radians(lat)/2))
MERC_ASPECT = ((LON_MAX - LON_MIN) * np.pi/180) / (_merc_y(LAT_MAX) - _merc_y(LAT_MIN))

PIXEL_DEG = 0.0002                               # lon pixel size
COLS = round((LON_MAX - LON_MIN) / PIXEL_DEG)   # ≈ 511
ROWS = round(COLS / MERC_ASPECT)                 # correct for Mercator display
print(f"Grid: {COLS} × {ROWS}  (Mercator aspect: {MERC_ASPECT:.3f})")

# ── Perlin noise helper ───────────────────────────────────────────────────────
# fBm: sum octaves of Perlin at increasing frequency, decreasing amplitude.
# Use c/cols and r/cols (same denominator) so noise increments are equal per
# pixel in both axes → features appear round in Web Mercator display.
def perlin_field(rows, cols, scale, octaves, persistence, lacunarity, base):
    """Return a (rows, cols) array of fBm Perlin noise, normalized to [0, 1]."""
    arr = np.empty((rows, cols), dtype=np.float32)
    for r in range(rows):
        for c in range(cols):
            arr[r, c] = pnoise2(
                c / cols * scale,
                r / cols * scale,  # cols, not rows — keeps noise isotropic
                octaves=octaves,
                persistence=persistence,
                lacunarity=lacunarity,
                base=base,
            )
    arr = (arr - arr.min()) / (arr.max() - arr.min())
    return arr

# ── Accessibility  (far=0 → near=1) ──────────────────────────────────────────
# Large scale (few broad hills) → smooth regional gradient.
acc = perlin_field(ROWS, COLS,
                   scale=3.0,       # ~3 full cycles across the extent
                   octaves=5,
                   persistence=0.5,
                   lacunarity=2.0,
                   base=0)

# ── Availability  (low=0 → high=1) ───────────────────────────────────────────
# Slightly smaller scale + more octaves → more varied texture.
avail = perlin_field(ROWS, COLS,
                     scale=5.0,
                     octaves=6,
                     persistence=0.45,
                     lacunarity=2.0,
                     base=7)

# ── Quantile classification (3 bins, 0 = low, 2 = high) ──────────────────────
def q3(a):
    return np.digitize(a, np.percentile(a, [100/3, 200/3])).astype(np.uint8)

acc_bin   = q3(acc)    # 0=far, 1=mid, 2=near
avail_bin = q3(avail)  # 0=low, 1=mid, 2=high

# ── Bivariate color matrix ────────────────────────────────────────────────────
#   rows    = accessibility (0=far … 2=near)
#   columns = availability  (0=low … 2=high)
# Flat list, row-major: [far-low, far-mid, far-high, mid-low, …, near-high]
_HEX = ["#E8E8E8", "#E4D9AC", "#C8B35A",
        "#CBB8D7", "#C8ADA0", "#AF8E53",
        "#9972AF", "#976B82", "#804D36"]

def _hex(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

COLORS = np.array([_hex(h) for h in _HEX], dtype=np.uint8).reshape(3, 3, 3)

# ── Build RGBA array ──────────────────────────────────────────────────────────
rgba = np.zeros((ROWS, COLS, 4), dtype=np.uint8)
rgba[:, :, 3] = 255
for a in range(3):
    for v in range(3):
        mask = (acc_bin == a) & (avail_bin == v)
        rgba[mask, :3] = COLORS[a, v]

# ── Helper: write GeoTIFF ─────────────────────────────────────────────────────
transform = from_bounds(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX, COLS, ROWS)

def write_tif(path, arrays, dtype, color_interp=None):
    profile = dict(
        driver='GTiff', height=ROWS, width=COLS,
        count=len(arrays), dtype=dtype,
        crs='EPSG:4326', transform=transform,
        compress='lzw', tiled=True,
    )
    with rasterio.open(path, 'w', **profile) as dst:
        for i, arr in enumerate(arrays, 1):
            dst.write(arr, i)
        if color_interp:
            dst.colorinterp = color_interp

# RGBA visualization
write_tif(RASTER_RGBA,
          [rgba[:, :, i] for i in range(4)],
          np.uint8,
          [ColorInterp.red, ColorInterp.green, ColorInterp.blue, ColorInterp.alpha])
print(f"Saved {RASTER_RGBA}")

# 2-band raw values
write_tif(RASTER_RAW,
          [acc.astype(np.float32), avail.astype(np.float32)],
          np.float32)
print(f"Saved {RASTER_RAW}")

# ── Legend PNG ────────────────────────────────────────────────────────────────
# Plain 3×3 color grid — labels are added in HTML
CELL = 60
leg = np.zeros((3 * CELL, 3 * CELL, 3), dtype=np.uint8)
for a in range(3):
    for v in range(3):
        r0 = (2 - a) * CELL   # flip: near at top
        c0 = v * CELL
        leg[r0:r0+CELL, c0:c0+CELL] = COLORS[a, v]

Image.fromarray(leg, 'RGB').save(LEGEND_OUT)
print(f"Saved {LEGEND_OUT}")
print()
print("Legend key (accessibility rows, availability columns):")
print("         avail:  Low       Mid       High")
for a, label in enumerate(['Far ', 'Mid ', 'Near']):
    row = '  '.join(f"#{COLORS[a,v,0]:02x}{COLORS[a,v,1]:02x}{COLORS[a,v,2]:02x}" for v in range(3))
    print(f"  acc: {label}  {row}")
