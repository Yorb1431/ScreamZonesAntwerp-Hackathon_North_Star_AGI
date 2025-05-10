# ────────────────────────────────────────────────────────────────────────────────
#  Scream-Zone Finder v2 – Antwerpen (Streamlit app)
#  Features
#  • Sidebar workflow: choose radius, filter zone-types, toggle layers
#  • Clear legend & metrics to avoid mis-communication
#  • Clustered markers + optional heatmap
#  • Download nearby zones as CSV
#  • Form with validation & helpful error messages
#  • All heavy data cached for speed
# ────────────────────────────────────────────────────────────────────────────────
import ast
import random
import requests
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from datasets import load_dataset
from folium.plugins import HeatMap, MarkerCluster
from geopy.distance import geodesic
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation

# ───────────────────────────── CONSTANTS ───────────────────────────────────────
APP_TITLE = "📣 Scream-Zone Finder – Antwerpen"
ANTWERP_CENTER = (51.2194, 4.4025)
ANTWERP_BOUNDS = dict(lat_min=51.1500, lat_max=51.3000,
                      lon_min=4.2500, lon_max=4.5200)

GOOGLE_API_KEY = "YOUR_GOOGLE_STREETVIEW_KEY"       # ← vul in of laat leeg
DATASET_ID = "ns2agi/antwerp-osm-navigator"         # Hugging Face dataset

ZONE_SPECS = {  # master spec for experimental zones
    "Forest":        dict(emoji="🌲", acoustics="High Echo & Isolated",
                          safety="✅ Safe",       rating="🔊🔊🔊🔊🔊"),
    "Tunnel":        dict(emoji="🎤", acoustics="Max Echo",
                          safety="⚠️ Sketchy",    rating="🔊🔊🔊🔊"),
    "Park":          dict(emoji="🌳", acoustics="Medium Echo & Visible",
                          safety="✅ Okay",       rating="🔊🔊🔊"),
    "Public Square": dict(emoji="🚫", acoustics="Loud but risky",
                          safety="❌ Avoid",      rating="🔇"),
    "Riverbank":     dict(emoji="🌊", acoustics="Melancholic vibes",
                          safety="✅ Peaceful",   rating="🔊🔊🔊🔊"),
    "Alley":         dict(emoji="🤫", acoustics="Echo but scary",
                          safety="⚠️ Not Ideal", rating="🔊🔊"),
}
EXPERIMENTAL_N = 60          # how many random bonus zones
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

# ──────────────────────────── PAGE CONFIG ──────────────────────────────────────
st.set_page_config(page_title="Scream Zone Finder",
                   layout="wide",
                   page_icon="📣")
st.title(APP_TITLE)

# ──────────────────────────── UTILITY FUNCS ────────────────────────────────────


def safe_parse(tag):
    """Safely turn HF stringified dict → real dict."""
    if isinstance(tag, dict):
        return tag
    if isinstance(tag, str) and tag.startswith("{"):
        try:
            return ast.literal_eval(tag)
        except Exception:
            return {}
    return {}


def classify_tags(tags):
    """Translate raw OSM tags → usable label for quiet zones."""
    if not tags:
        return "⚠️ Onzeker"
    if any(k in tags for k in ["building", "addr:street", "addr:housenumber"]):
        return "❌ Niet geschikt (bebouwd)"
    if any(k in tags for k in ["highway", "railway", "amenity"]):
        return "❌ Niet geschikt (verkeer/voorzieningen)"
    if tags.get("landuse") == "industrial":
        return "✅ Industriegebied"
    if tags.get("natural") in ["wood", "scrub", "heath"]:
        return "✅ Natuurgebied"
    if tags.get("service") in ["alley", "industrial"]:
        return "✅ Afgelegen zone"
    if not any(k in tags for k in ["building", "addr:street", "highway",
                                   "railway", "amenity"]):
        return "✅ Rustige plek"
    return "⚠️ Onzeker"


def marker_color(label_or_rating: str) -> str:
    """Green good, orange meh, red avoid."""
    if ("✅" in label_or_rating) or ("🔊🔊🔊🔊" in label_or_rating):
        return "green"
    if ("❌" in label_or_rating) or ("🔇" in label_or_rating):
        return "red"
    return "orange"


def rnd_coord(bounds):
    """Random lat/lon inside Antwerp bounding box."""
    lat = random.uniform(bounds["lat_min"], bounds["lat_max"])
    lon = random.uniform(bounds["lon_min"], bounds["lon_max"])
    return lat, lon


# ────────────────────────── DATA LOADING (CACHED) ─────────────────────────────
@st.cache_data(show_spinner="🛰️ OSM-data laden…", ttl=24 * 3600)
def load_osm_clean() -> pd.DataFrame:
    """Download HF dataset, clean, keep only potential quiet zones."""
    hf_ds = load_dataset(DATASET_ID)
    df = (hf_ds["train"]
          .to_pandas()[["lat", "lon", "tags"]]
          .dropna())
    df["tags"] = df["tags"].apply(safe_parse)
    df["label"] = df["tags"].apply(classify_tags)
    df = df[df["label"].str.startswith("✅")].copy()
    return df


@st.cache_data(ttl=24 * 3600)
def generate_random_zones(n=EXPERIMENTAL_N) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        z_type = random.choice(list(ZONE_SPECS.keys()))
        spec = ZONE_SPECS[z_type]
        lat, lon = rnd_coord(ANTWERP_BOUNDS)
        rows.append(dict(
            lat=lat, lon=lon,
            label=f"{spec['emoji']} {z_type}",
            acoustics=spec["acoustics"],
            safety=spec["safety"],
            rating=spec["rating"]
        ))
    return pd.DataFrame(rows)


def distance_m(p1, p2) -> float:
    return geodesic(p1, p2).meters


# ────────────────────────── GET USER LOCATION ─────────────────────────────────
def get_user_location() -> tuple[float, float]:
    if "user_loc" in st.session_state:
        return st.session_state.user_loc

    loc = get_geolocation()
    if loc is None:
        st.info("📍 Kon je browser-locatie niet ophalen; "
                "ik zet je even op Antwerpen-Centraal.")
        coords = ANTWERP_CENTER
    else:
        coords = (loc["coords"]["latitude"], loc["coords"]["longitude"])
    st.session_state.user_loc = coords
    return coords


user_loc = get_user_location()
st.success(f"✅ Jouw coördinaten: {user_loc[0]:.5f}, {user_loc[1]:.5f}")

# ─────────────────────────── SIDEBAR UI ───────────────────────────────────────
with st.sidebar:
    st.header("🔧 Instellingen")
    search_radius = st.slider("Zoekradius (meter)", 100, 2000, 500, 50)
    st.caption("Alle stille OSM-zones binnen deze straal worden getoond.")

    zone_choices = list(ZONE_SPECS.keys())
    active_zone_types = st.multiselect(
        "Toon experimentele zone-types",
        options=zone_choices,
        default=zone_choices,
    )

    show_experimental = st.checkbox(
        "Toon experimentele random zones", value=True)
    show_heatmap = st.checkbox("Toon heatmap", value=True)

    st.markdown("### 📑 Legenda")
    legend_md = "\n".join(
        f"{spec['emoji']} **{z_type}** – {spec['rating']}"
        for z_type, spec in ZONE_SPECS.items()
    )
    st.markdown(legend_md)
    st.markdown("---")
    st.markdown("👈 Pas instellingen aan en bekijk de kaart ➡️")

# ──────────────────────── DATA PREPARATION ───────────────────────────────────
osm_df = load_osm_clean()
osm_df["afstand_m"] = osm_df.apply(
    lambda r: distance_m(user_loc, (r["lat"], r["lon"])), axis=1)

nearby_osm = osm_df[osm_df["afstand_m"] <= search_radius].sort_values(
    "afstand_m")

# Experimental
if show_experimental:
    rnd_df = generate_random_zones()
    rnd_df = rnd_df[rnd_df["label"].str.contains("|".join(active_zone_types))]
else:
    rnd_df = pd.DataFrame([])

# Metrics to avoid mis-communication
col_a, col_b, col_c = st.columns(3)
col_a.metric("OSM-zones binnen straal", len(nearby_osm))
col_b.metric("Experimentele zones", len(rnd_df))
col_c.metric("Totale markers", len(nearby_osm) + len(rnd_df))

# ────────────────────────── FOLIUM MAP ────────────────────────────────────────
m = folium.Map(location=user_loc, zoom_start=14, control_scale=True)

# user marker
folium.Marker(
    location=user_loc,
    tooltip="Hier ben jij",
    icon=folium.DivIcon(html="<div style='font-size:34px;'>🧘</div>")
).add_to(m)

# clustered layers
osm_cluster = MarkerCluster(name="OSM zones").add_to(m)
rnd_cluster = MarkerCluster(name="Experimenteel").add_to(m)

# OSM markers
for _, r in nearby_osm.iterrows():
    lat, lon = r["lat"], r["lon"]
    label = r["label"]
    color = marker_color(label)
    popup = folium.Popup(f"<b>{label}</b><br>Afstand: {r['afstand_m']:.0f} m",
                         max_width=250)
    folium.Marker(
        location=[lat, lon],
        popup=popup,
        icon=folium.Icon(color=color, icon="volume-up")
    ).add_to(osm_cluster)

# Experimental markers
for _, r in rnd_df.iterrows():
    lat, lon = r["lat"], r["lon"]
    html = (f"<b>{r['label']}</b><br>"
            f"Acoustics: {r['acoustics']}<br>"
            f"Safety: {r['safety']}<br>"
            f"Rating: {r['rating']}")
    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(html, max_width=250),
        icon=folium.DivIcon(
            html=f"<div style='font-size:22px;'>{r['label'].split()[0]}</div>")
    ).add_to(rnd_cluster)

# Optional heatmap
if show_heatmap and not nearby_osm.empty:
    heat_data = nearby_osm[["lat", "lon"]].values.tolist()
    HeatMap(heat_data, radius=12, blur=15,
            min_opacity=0.3, name="Heatmap").add_to(m)

folium.LayerControl().add_to(m)

# Render map
st.subheader("🗺️ Kaartweergave")
st_folium(m, height=600, width=750)

# ───────────────────────── DOWNLOAD BUTTON ────────────────────────────────────
if not nearby_osm.empty:
    csv = nearby_osm[["lat", "lon", "label", "afstand_m"]].to_csv(index=False)
    st.download_button("⬇️ Download deze zones (CSV)",
                       data=csv,
                       file_name="scream_zones_nearby.csv",
                       mime="text/csv")

# ────────────────────────── SUGGESTION FORM ───────────────────────────────────
st.divider()
st.subheader("📬 Stel een nieuwe scream-zone voor")


def within_antwerp(lat, lon) -> bool:
    return (ANTWERP_BOUNDS["lat_min"] <= lat <= ANTWERP_BOUNDS["lat_max"]
            and ANTWERP_BOUNDS["lon_min"] <= lon <= ANTWERP_BOUNDS["lon_max"])


with st.form("suggest_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Naam (optioneel)")
        lat_in = st.number_input("Breedtegraad (lat)", format="%.6f")
    with col2:
        zone_kind = st.selectbox("Type zone", ["Rustig", "Natuurgebied",
                                               "Industrie", "Anders"])
        lon_in = st.number_input("Lengtegraad (lon)", format="%.6f")
    note = st.text_area("Waarom is dit een goeie plek om te schreeuwen?")
    submit = st.form_submit_button("✅ Verstuur")

    if submit:
        if not within_antwerp(lat_in, lon_in):
            st.error("⛔ Coördinaten liggen buiten Antwerpen – pas ze aan.")
            st.stop()
        path = Path("suggested_zones.csv")
        new_row = pd.DataFrame([dict(
            naam=name or "🕵️ Anoniem",
            lat=lat_in, lon=lon_in,
            type=zone_kind, opmerking=note
        )])
        new_row.to_csv(path, mode="a", header=not path.exists(), index=False)
        st.success("Bedankt voor je suggestie! 🎉")

# Show submitted suggestions
path = Path("suggested_zones.csv")
if path.exists():
    st.markdown("### 📄 Ingestuurde scream-zones")
    st.dataframe(pd.read_csv(path))

# ──────────────────────────── FOOTER ──────────────────────────────────────────
st.caption("Data: OpenStreetMap × Hugging Face — Tool by Yorbe & Angelo 🚀")
