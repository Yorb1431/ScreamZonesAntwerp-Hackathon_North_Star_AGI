# ────────────────────────────────────────────────────────────────────────────────
#  Scream-Zone Finder v3 – Antwerpen
# ────────────────────────────────────────────────────────────────────────────────
import ast
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

GOOGLE_KEY = "YOUR_GOOGLE_STREETVIEW_KEY"
DATASET_ID = "ns2agi/antwerp-osm-navigator"

ZONE_SPECS = {
    "Forest":  dict(emoji="🌲", kw="forest",  acoust="Echo & stil",        safe="✅ Safe",    rate="🔊🔊🔊🔊🔊"),
    "Tunnel":  dict(emoji="🎤", kw="tunnel",  acoust="Max echo",          safe="⚠️ Sketchy", rate="🔊🔊🔊🔊"),
    "Park":    dict(emoji="🌳", kw="park",    acoust="Zichtbaar",         safe="✅ Okay",    rate="🔊🔊🔊"),
    "Square":  dict(emoji="🚫", kw="square",  acoust="Luid & riskant",    safe="❌ Avoid",   rate="🔇"),
    "River":   dict(emoji="🌊", kw="river",   acoust="Melancholisch",     safe="✅ Peace",   rate="🔊🔊🔊🔊"),
    "Alley":   dict(emoji="🤫", kw="alley",   acoust="Echo maar eng",     safe="⚠️ Meh",    rate="🔊🔊"),
}
EXPERIMENTAL_N = 60
RND_SEED = 42
random.seed(RND_SEED)

# ─────────── STREAMLIT CONFIG ───────────
st.set_page_config(layout="wide", page_icon="📣", page_title="Scream-Zone Finder")
st.title(APP_TITLE)

# ─────────── HELPER STATE ───────────
st.session_state.fallback_active = False

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

def place_image(lat, lon, kw=None):
    if GOOGLE_KEY and GOOGLE_KEY != "YOUR_GOOGLE_STREETVIEW_KEY":
        url = (f"https://maps.googleapis.com/maps/api/streetview"
               f"?size=400x250&location={lat},{lon}&fov=80&heading=70&pitch=0&key={GOOGLE_KEY}")
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200 and b"<html" not in r.content and len(r.content) > 1500:
                return url
            else:
                st.session_state.fallback_active = True
        except Exception:
            st.session_state.fallback_active = True
    else:
        st.session_state.fallback_active = True
    fallback_kw = kw or random.choice(["quiet", "park", "forest", "industrial", "street", "nature"])
    return f"https://source.unsplash.com/400x250/?{fallback_kw}"

@st.cache_data(ttl=24*3600, show_spinner="OSM-data laden…")
def load_osm():
    ds = load_dataset(DATASET_ID)["train"].to_pandas()
    df = ds[["lat", "lon", "tags"]].dropna()
    df["tags"] = df["tags"].apply(safe_parse)
    df["label"] = df["tags"].apply(classify)
    df = df[df["label"].str.startswith("✅")].copy()
    return df

@st.cache_data(ttl=24*3600)
def experimental_df():
    rows = []
    for _ in range(EXPERIMENTAL_N):
        z = random.choice(list(ZONE_SPECS))
        spec = ZONE_SPECS[z]
        lat, lon = rnd_coord()
        rows.append(dict(lat=lat, lon=lon, ztype=z, **spec))
    return pd.DataFrame(rows)

def geodist(p1, p2): return geodesic(p1, p2).meters

# ─────────── LOCATION ───────────
def get_user_loc():
    if "loc" in st.session_state:
        return st.session_state.loc
    loc = get_geolocation()
    if loc:
        coords = (loc["coords"]["latitude"], loc["coords"]["longitude"])
    else:
        coords = ANTWERP_CENTER
        st.info("Kon geen browser-locatie ophalen — centrum Antwerpen wordt gebruikt.")
    st.session_state.loc = coords
    return coords

user_loc = get_user_loc()
st.success(f"✅ Je bent hier: {user_loc[0]:.5f}, {user_loc[1]:.5f}")

# ─────────── FOUTMELDING ───────────
if st.session_state.fallback_active:
    st.warning("📷 Street View kon niet geladen worden — virtuele beelden via Unsplash worden getoond.")
