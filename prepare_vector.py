#!/usr/bin/env python3
"""
Prepare vector dataset: clip tlm_hoheitsgebiet to bbox,
assign Accessibility and Availability by sampling bivariate_raw.tif
at each polygon centroid, save as GeoJSON for Leaflet.

Run AFTER generate_raster.py (requires bivariate_raw.tif).
"""

import numpy as np
import geopandas as gpd
import rasterio
from shapely.geometry import box
from shapely.ops import transform as shp_transform
import pyproj

from config import (LON_MIN, LAT_MIN, LON_MAX, LAT_MAX,
                    GPKG_PATH, GPKG_LAYER, RASTER_RAW, VECTOR_OUT)

# ── Load ──────────────────────────────────────────────────────────────────────
print(f"Loading {GPKG_LAYER} from {GPKG_PATH} ...")
gdf = gpd.read_file(GPKG_PATH, layer=GPKG_LAYER)
print(f"  {len(gdf)} features, CRS: {gdf.crs}")

# ── Reproject to WGS84 ────────────────────────────────────────────────────────
gdf = gdf.to_crs('EPSG:4326')

# Drop Z coordinates if present (SwissBOUNDARIES3D has Z; GeoJSON needs 2D)
import shapely
gdf['geometry'] = shapely.force_2d(gdf.geometry.values)

# ── Clip to bbox ──────────────────────────────────────────────────────────────
bbox = box(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX)
clipped = gdf[gdf.geometry.intersects(bbox)].copy()
clipped['geometry'] = clipped.geometry.intersection(bbox)
clipped = clipped[~clipped.geometry.is_empty].reset_index(drop=True)
print(f"  {len(clipped)} features within bbox")

# ── Sample raster at centroids ────────────────────────────────────────────────
print(f"Sampling {RASTER_RAW} at polygon centroids ...")
centroids = clipped.geometry.centroid
coords = [(pt.x, pt.y) for pt in centroids]

with rasterio.open(RASTER_RAW) as src:
    sampled = np.array(list(src.sample(coords)))   # shape (n, 2)
    nodata  = src.nodata or -9999

acc_vals   = sampled[:, 0].astype(float)
avail_vals = sampled[:, 1].astype(float)

# Handle nodata (centroid fell outside raster extent)
acc_vals[acc_vals == nodata]     = 0.5
avail_vals[avail_vals == nodata] = 0.5

# ── Classify ──────────────────────────────────────────────────────────────────
def classify(vals, labels):
    """Split [0,1] into thirds and map to labels."""
    out = np.empty(len(vals), dtype=object)
    out[vals <  1/3] = labels[0]
    out[(vals >= 1/3) & (vals < 2/3)] = labels[1]
    out[vals >= 2/3] = labels[2]
    return out

clipped['accessibility'] = classify(acc_vals,   ['far',  'med',  'near'])
clipped['availability']  = classify(avail_vals,  ['low',  'med',  'high'])

# ── Keep useful columns ───────────────────────────────────────────────────────
print(f"  Columns in source: {list(clipped.columns)}")
desired = ['NAME', 'BFS_NUMMER', 'KANTONSNUM', 'OBJEKTART',
           'accessibility', 'availability', 'geometry']
keep = [c for c in desired if c in clipped.columns]
clipped = clipped[keep]

# ── Save ──────────────────────────────────────────────────────────────────────
clipped.to_file(VECTOR_OUT, driver='GeoJSON')
print(f"Saved {VECTOR_OUT}  ({len(clipped)} features)")
print()
print(clipped[['NAME', 'accessibility', 'availability']
              if 'NAME' in clipped.columns
              else ['accessibility', 'availability']].to_string())
