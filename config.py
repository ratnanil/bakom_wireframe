"""
Shared configuration — edit this file to change extent or paths.
Both generate_raster.py and prepare_vector.py import from here.
"""

# ── Bounding box (WGS84 / EPSG:4326) ─────────────────────────────────────────
import fiona
with fiona.open('boundingbox.gpkg') as _src:
    LON_MIN, LAT_MIN, LON_MAX, LAT_MAX = _src.bounds

# ── Input files ───────────────────────────────────────────────────────────────
GPKG_PATH  = 'swissBOUNDARIES3D_1_5_LV95_LN02.gpkg'
GPKG_LAYER = 'tlm_hoheitsgebiet'

# ── Output files ──────────────────────────────────────────────────────────────
RASTER_RGBA = 'bivariate.tif'
RASTER_RAW  = 'bivariate_raw.tif'
VECTOR_OUT  = 'gemeindegrenze.geojson'
LEGEND_OUT  = 'legend.png'
