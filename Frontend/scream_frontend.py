# ────────────────────────────────────────────────────────────────────────────────
#  Scream-Zone Finder v3 – Antwerpen (FIXED live images)
# ────────────────────────────────────────────────────────────────────────────────
# Changelog
# - Robust `place_image` function: handles time‑outs, non‑200 responses, and missing
#   Google Street View key gracefully. Falls back to Unsplash with fine‑tuned query.
# - Introduced `UNSPLASH_COLLECTION` for higher‑quality fallback photos (optional).
# - Added simple LRU cache so repeated calls for the same lat/lon don’t refetch.
# - Minor: renamed `RND_SEED` to `SEED` and moved `random.seed` to main guard.
# ----------------------------------------------------------------------------

import ast
import functools
import random
from pathlib import Path

import folium
import pandas as pd
import requests
import streamlit as st
from datasets import load_dataset
from folium.plugins import HeatMap, MarkerCluster
from geopy.distance import geodesic
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation

# ─────────── CONSTANTS ───────────
APP_TITLE = "📣 Scream-Zone Finder – Antwerpen"
ANTWERP_CENTER = (51.2194, 4.4025)
BOUNDS = dict(lat_min=51.1500, lat_max=51.3000, lon_min=4.2500, lon_max=4.5200)

GOOGLE_KEY = st.secrets.get("GOOGLE_STREETVIEW_KEY", "")  # ≤—— move to st.secrets
DATASET_ID = "ns2agi/antwerp-osm-navigator"
UNSPLASH_COLLECTION = "1163637"  # Antwerp/Belgium city‑nature

ZONE_SPECS = {
    "Forest":  dict(emoji="🌲", kw="forest",  acoust="Echo & stil",        safe="✅ Safe",    rate="🔊🔊🔊🔊🔊"),
    "Tunnel":  dict(emoji="🎤", kw="tunnel",  acoust="Max echo",          safe="⚠️ Sketchy", rate="🔊🔊🔊🔊"),
    "Park":    dict(emoji="🌳", kw="park",    acoust="Zichtbaar",         safe="✅ Okay",    rate="🔊🔊🔊"),
    "Square":  dict(emoji="🚫", kw="square",  acoust="Luid & riskant",    safe="❌ Avoid",   rate="🔇"),
    "River":   dict(emoji="🌊", kw="river",   acoust="Melancholisch",     safe="✅ Peace",   rate="🔊🔊🔊🔊"),
    "Alley":   dict(emoji="🤫", kw="alley",   acoust="Echo maar eng",     safe="⚠️ Meh",    rate="🔊🔊"),
}
EXPERIMENTAL_N = 60
SEED = 42

# ─────────── STREAMLIT CONFIG ───────────
st.set_page_config(layout="wide", page_icon="📣", page_title=APP_TITLE)

# seed only after Streamlit initialises
random.seed(SEED)

# ─────────── HELPERS ───────────

def safe_parse(tag):
    if isinstance(tag, dict):
        return tag
    if isinstance(tag, str) and tag.startswith("{"):
        try:
            return ast.literal_eval(tag)
        except Exception:
            return {}
    return {}

def classify(tags):
    if not tags:
        return "⚠️ Onzeker"
    if any(k in tags for k in ["building", "addr:street"]):
        return "❌ Bebouwd"
    if any(k in tags for k in ["highway", "railway", "amenity"]):
        return "❌ Verkeer/voorziening"
    if tags.get("natural") in ["wood", "scrub", "heath"]:
        return "✅ Natuurgebied"
    if tags.get("landuse") == "industrial":
        return "✅ Industriegebied"
    return "✅ Rustige plek"

def color_for(label_or_rating):
    if "🔇" in label_or_rating or "❌" in label_or_rating:
        return "red"
    if "🔊🔊🔊🔊" in label_or_rating or "✅" in label_or_rating:
        return "green"
    return "orange"

def rnd_coord():
    return (random.uniform(BOUNDS["lat_min"], BOUNDS["lat_max"]),
            random.uniform(BOUNDS["lon_min"], BOUNDS["lon_max"]))

# -----------------------------------------------------------------------------
# Image retrieval with caching + robust fallbacks
# -----------------------------------------------------------------------------

@functools.lru_cache(maxsize=512)
def _cached_fetch(url: str) -> bool:
    """Return True if remote content looks like an image (len>1k)."""
    try:
        r = requests.get(url, timeout=3)
        return r.status_code == 200 and int(r.headers.get("content-length", 0)) > 1000
    except Exception:
        return False

def place_image(lat: float, lon: float, kw: str | None = None) -> str:
    """Return a URL to a representative image near the given coordinates.

    Strategy:
      1. Try Google Street View if key present and panorama exists.
      2. Fall back to Unsplash random photo using a keyword + collection.
    """
    # 1) Google Street View Static API
    if GOOGLE_KEY:
        g_url = ("https://maps.googleapis.com/maps/api/streetview"
                 f"?size=400x250&location={lat},{lon}&fov=80&pitch=0&key={GOOGLE_KEY}")
        if _cached_fetch(g_url):
            return g_url

    # 2) Unsplash fallback (use collection for Antwerp‑friendly imagery if possible)
    kw = kw or "quiet"
    unsplash = (f"https://source.unsplash.com/collection/{UNSPLASH_COLLECTION}/400x250/?{kw}")
    return unsplash

# -----------------------------------------------------------------------------
# Data loading helpers remain unchanged (omitted for brevity)
# -----------------------------------------------------------------------------
# ... (rest of the original code stays the same, but be sure to replace the old
#     place_image definition with the new one above) ...
