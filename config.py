"""
Shared configuration — edit this file to change extent or paths.
Both generate_raster.py and prepare_vector.py import from here.
"""

# ── Bounding box (WGS84 / EPSG:4326) ─────────────────────────────────────────
LON_MIN, LAT_MIN = 8.631302, 47.393974
LON_MAX, LAT_MAX = 8.828406, 47.511779

# ── Input files ───────────────────────────────────────────────────────────────
GPKG_PATH  = 'swissBOUNDARIES3D_1_5_LV95_LN02.gpkg'
GPKG_LAYER = 'tlm_hoheitsgebiet'

# ── Output files ──────────────────────────────────────────────────────────────
RASTER_RGBA = 'bivariate.tif'
RASTER_RAW  = 'bivariate_raw.tif'
VECTOR_OUT  = 'gemeindegrenze.geojson'
LEGEND_OUT  = 'legend.png'
