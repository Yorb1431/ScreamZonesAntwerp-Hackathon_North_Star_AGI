# ────────────────────────────────────────────────────────────────────────────────
#  Scream-Zone Finder v3.1 – Antwerpen  (met gegarandeerde afbeeldingen)
# ────────────────────────────────────────────────────────────────────────────────
import ast
import os
import random
import json
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
CENTER = (51.2194, 4.4025)
BOX = dict(lat_min=51.1500, lat_max=51.3000, lon_min=4.2500, lon_max=4.5200)

# Lees Street-View-key uit secrets of env
GOOGLE_KEY = st.secrets.get("GCP_STREETVIEW_KEY",
                            os.getenv("GOOGLE_STREETVIEW_KEY", "")).strip()

DATASET_ID = "ns2agi/antwerp-osm-navigator"
ZONE_SPECS = {
    "Forest":  dict(emoji="🌲", kw="forest",  acoust="Echo & stil",
                    safe="✅ Safe",    rate="🔊🔊🔊🔊🔊"),
    "Tunnel":  dict(emoji="🎤", kw="tunnel",  acoust="Max echo",
                    safe="⚠️ Sketchy", rate="🔊🔊🔊🔊"),
    "Park":    dict(emoji="🌳", kw="park",    acoust="Zichtbaar",
                    safe="✅ Okay",    rate="🔊🔊🔊"),
    "Square":  dict(emoji="🚫", kw="square",  acoust="Luid & riskant",
                    safe="❌ Avoid",   rate="🔇"),
    "River":   dict(emoji="🌊", kw="river",   acoust="Melancholisch",
                    safe="✅ Peace",   rate="🔊🔊🔊🔊"),
    "Alley":   dict(emoji="🤫", kw="alley",   acoust="Echo maar eng",
                    safe="⚠️ Meh",    rate="🔊🔊"),
}
EXPERIMENTAL_N, RND_SEED = 60, 42
random.seed(RND_SEED)

# ─────────── STREAMLIT CONFIG ───────────
st.set_page_config(layout="wide", page_icon="📣", page_title=APP_TITLE)
st.title(APP_TITLE)

# ─────────── HELPERS ───────────


def safe_parse(tag):
    if isinstance(tag, dict):
        return tag
    if isinstance(tag, str) and tag.startswith("{"):
        try:
            return ast.literal_eval(tag)
        except:
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


def colour(label_or_rating: str):
    if "🔇" in label_or_rating or "❌" in label_or_rating:
        return "red"
    if "🔊🔊🔊🔊" in label_or_rating or "✅" in label_or_rating:
        return "green"
    return "orange"


def rnd_coord():  # random punt in bounding-box
    return random.uniform(BOX["lat_min"], BOX["lat_max"]), \
        random.uniform(BOX["lon_min"], BOX["lon_max"])

# ---------- IMAGE HANDLING ----------------------------------------------------


@st.cache_data(ttl=24*3600, show_spinner=False)
def streetview_url(lat, lon, size="300x200"):
    """Return StreetView URL - or None if Google says no image."""
    if not GOOGLE_KEY:
        return None
    meta = ("https://maps.googleapis.com/maps/api/streetview/metadata"
            f"?location={lat},{lon}&key={GOOGLE_KEY}")
    try:
        status = requests.get(meta, timeout=2).json().get("status")
        if status == "OK":
            return ("https://maps.googleapis.com/maps/api/streetview"
                    f"?size={size}&location={lat},{lon}&key={GOOGLE_KEY}")
    except Exception:
        pass
    return None


@st.cache_data(ttl=24*3600, show_spinner=False)
def place_image(lat, lon, kw="quiet"):
    """Guaranteed image URL for popup."""
    url = streetview_url(lat, lon)
    if url:
        return url
    return f"https://source.unsplash.com/300x200/?{kw}"

# ---------- DATA LOADING ------------------------------------------------------


@st.cache_data(ttl=24*3600, show_spinner="OSM-data laden…")
def load_osm():
    df = load_dataset(DATASET_ID)["train"].to_pandas()[["lat", "lon", "tags"]]
    df["tags"] = df["tags"].apply(safe_parse)
    df["label"] = df["tags"].apply(classify)
    return df[df.label.str.startswith("✅")].copy()


@st.cache_data(ttl=24*3600)
def random_df():
    rows = []
    for _ in range(EXPERIMENTAL_N):
        z = random.choice(list(ZONE_SPECS))
        spec = ZONE_SPECS[z]
        lat, lon = rnd_coord()
        rows.append(dict(lat=lat, lon=lon, ztype=z, **spec))
    return pd.DataFrame(rows)


def dist(a, b): return geodesic(a, b).meters

# ---------- GET USER LOCATION -------------------------------------------------


def user_loc():
    if "loc" in st.session_state:
        return st.session_state.loc
    loc = get_geolocation()
    coords = (loc["coords"]["latitude"], loc["coords"]
              ["longitude"]) if loc else CENTER
    st.session_state.loc = coords
    return coords


me = user_loc()
st.success(f"✅ Je bent hier: {me[0]:.5f}, {me[1]:.5f}")

# ---------- SIDEBAR -----------------------------------------------------------
with st.sidebar:
    st.header("Instellingen")
    radius = st.slider("Zoekradius (m)", 100, 2000, 500, 50)
    show_ppl = st.checkbox("Toon andere gebruikers", True)
    show_osm = st.checkbox("Toon OSM-zones", True)
    show_exp = st.checkbox("Toon experimentele zones", True)
    show_heat = st.checkbox("Heatmap", False)

    if not GOOGLE_KEY:
        st.warning(
            "🔑 Voeg een Google Street-View API-key toe om echte foto’s te krijgen.")
    st.markdown("---")
    st.markdown("### Legenda")
    st.markdown(
        "🧍 **Andere gebruiker**  \n🟢 **Aanbevolen**  \n🔴 **Vermijden**  \n🟠 **Experimenteel**")

# ---------- DATA PREP ---------------------------------------------------------
osm = load_osm()
osm["dist"] = osm.apply(lambda r: dist(me, (r.lat, r.lon)), axis=1)
near_osm = osm[osm.dist <= radius]
exp = random_df() if show_exp else pd.DataFrame()

# ---------- METRICS -----------------------------------------------------------
a, b, c = st.columns(3)
a.metric("OSM-zones", len(near_osm))
b.metric("Experimenteel", len(exp))
c.metric("Radius", radius, "m")

# ---------- MAP ---------------------------------------------------------------
m = folium.Map(location=me, zoom_start=14, control_scale=True)
folium.Marker(me, tooltip="Dit ben jij",
              icon=folium.DivIcon(html="<div style='font-size:34px;'>🧘</div>")).add_to(m)

ppl_grp = MarkerCluster(name="🙋 Gebruikers").add_to(m)
osm_grp = MarkerCluster(name="🟢 Aanbevolen").add_to(m)
bad_grp = MarkerCluster(name="🔴 Vermijden").add_to(m)
exp_grp = MarkerCluster(name="🟠 Experimenteel").add_to(m)

# fake users
if show_ppl:
    for _ in range(25):
        lat, lon = rnd_coord()
        folium.Marker([lat, lon], tooltip="Andere gebruiker",
                      icon=folium.DivIcon(
                          html=f"<div style='font-size:24px;'>{random.choice(['😎','👽','🐸','😱','🤖'])}</div>")
                      ).add_to(ppl_grp)

# OSM markers
if show_osm:
    for _, r in near_osm.iterrows():
        img = place_image(r.lat, r.lon, "quiet")
        html = (f"<a href='{img}' target='_blank'>"
                f"<img src='{img}' width='250'></a><br>"
                f"<b>{r.label}</b><br>Afstand {r.dist:.0f} m")
        folium.Marker([r.lat, r.lon],
                      popup=folium.Popup(html, max_width=270),
                      icon=folium.Icon(color="green", icon="volume-up")
                      ).add_to(osm_grp)

# experimental
for _, r in exp.iterrows():
    img = place_image(r.lat, r.lon, r.kw)
    html = (f"<a href='{img}' target='_blank'>"
            f"<img src='{img}' width='250'></a><br>"
            f"<b>{r.emoji} {r.ztype}</b><br>Acoustics: {r.acoust}<br>Safety: {r.safe}<br>Rating: {r.rate}")
    grp = bad_grp if ("🔇" in r.rate or "❌" in r.safe) else exp_grp
    folium.Marker([r.lat, r.lon],
                  popup=folium.Popup(html, max_width=270),
                  icon=folium.Icon(color=colour(r.rate), icon="volume-up")
                  ).add_to(grp)

# heatmap
if show_heat and not near_osm.empty:
    HeatMap(near_osm[["lat", "lon"]].values.tolist(),
            radius=12, blur=15, min_opacity=0.3,
            name="Heatmap").add_to(m)

folium.LayerControl().add_to(m)

# ---------- RENDER ------------------------------------------------------------
st.subheader("🗺️ Kaart")
st_folium(m, height=600, width=820)

st.caption("Data : OpenStreetMap × Hugging Face — Tool by Yorbe & Angelo 🚀")
