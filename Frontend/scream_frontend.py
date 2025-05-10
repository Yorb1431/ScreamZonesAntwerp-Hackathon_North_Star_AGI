import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from geopy.distance import geodesic
from datasets import load_dataset
import ast
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
import random

# ====== Functies ======


def safe_parse(tag):
    if isinstance(tag, dict):
        return tag
    if isinstance(tag, str) and tag.startswith('{'):
        try:
            return ast.literal_eval(tag)
        except:
            return {}
    return {}


def classify_tags(tags):
    if not tags or tags == {}:
        return "⚠️ Onzeker"
    if 'building' in tags or 'addr:street' in tags or 'addr:housenumber' in tags:
        return "❌ Niet geschikt (bebouwd)"
    if 'highway' in tags or 'railway' in tags or 'amenity' in tags:
        return "❌ Niet geschikt (verkeer/voorzieningen)"
    if tags.get('landuse') == 'industrial':
        return "✅ Industriegebied"
    if tags.get('natural') in ['wood', 'scrub', 'heath']:
        return "✅ Natuurgebied"
    if tags.get('service') in ['alley', 'industrial']:
        return "✅ Afgelegen zone"
    if not any(k in tags for k in ['building', 'addr:street', 'highway', 'railway', 'amenity']):
        return "✅ Rustige plek"
    return "⚠️ Onzeker"


def kleur(label):
    if "✅" in label:
        return "green"
    elif "❌" in label:
        return "red"
    else:
        return "orange"


@st.cache_data
def load_and_classify():
    dataset = load_dataset("ns2agi/antwerp-osm-navigator")
    df = dataset['train'].to_pandas()
    df = df[['lat', 'lon', 'tags']].dropna()
    df['tags_parsed'] = df['tags'].apply(safe_parse)
    df['label'] = df['tags_parsed'].apply(classify_tags)
    return df[df['label'].str.startswith("✅")].copy()

# ====== App Start ======


st.set_page_config(page_title="Scream Zone Finder", layout="wide")
st.title("📣 Vind de dichtstbijzijnde Scream Zone in Antwerpen")

location = get_geolocation()

if location is None:
    st.warning("📍 Je locatie wordt opgehaald... Sta het toe in je browser.")
    st.stop()

lat = location['coords']['latitude']
lon = location['coords']['longitude']
user_loc = (lat, lon)

st.success(f"✅ Je locatie is: {round(lat, 5)}, {round(lon, 5)}")

# Dataset laden en klassificeren
df = load_and_classify()
df['afstand_m'] = df.apply(lambda row: geodesic(
    user_loc, (row['lat'], row['lon'])).meters, axis=1)

# 🔘 Filters
st.subheader("🔍 Filteropties")
if 'filter_active' not in st.session_state:
    st.session_state.filter_active = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🧭 Waar kan ik NU schreeuwen?"):
        st.session_state.filter_active = True
with col2:
    if st.button("🔄 Toon alle scream zones"):
        st.session_state.filter_active = False

if st.session_state.filter_active:
    filtered_df = df[df['afstand_m'] <= 500].sort_values('afstand_m')
    st.subheader("📍 Scream zones binnen 500 meter")
    if filtered_df.empty:
        st.warning(
            "😢 Geen scream zone binnen 500 meter. Misschien even wandelen?")
else:
    filtered_df = df.sort_values('afstand_m').head(5)
    st.subheader("📍 Dichtstbijzijnde scream zones")

# 🌍 Kaart genereren
m = folium.Map(location=user_loc, zoom_start=14)

# 🧠 Jij als karakter op de kaart
folium.Marker(
    location=user_loc,
    popup="🧠 Hier ben ik – je scream buddy!",
    icon=folium.DivIcon(html=f"""<div style='font-size:24px;'>🧠</div>""")
).add_to(m)

# 👥 Andere willekeurige screamers
other_emojis = ["😎", "👽", "🐸", "🧛", "😱", "🤖", "🧌"]
for _ in range(8):
    offset_lat = random.uniform(-0.004, 0.004)
    offset_lon = random.uniform(-0.004, 0.004)
    folium.Marker(
        location=[user_loc[0] + offset_lat, user_loc[1] + offset_lon],
        popup="Een andere scream visitor...",
        icon=folium.DivIcon(
            html=f"""<div style='font-size:24px;'>{random.choice(other_emojis)}</div>""")
    ).add_to(m)

# 📌 Toon scream zones op kaart
for _, row in filtered_df.iterrows():
    folium.Marker(
        location=[row['lat'], row['lon']],
        popup=f"{row['label']} ({round(row['afstand_m'])} m)",
        icon=folium.Icon(color=kleur(row['label']), icon='volume-up')
    ).add_to(m)

# 🔥 Heatmap toevoegen
heat_data = [[row['lat'], row['lon']] for _, row in df.iterrows()]
HeatMap(heat_data, radius=12, blur=15, min_opacity=0.3).add_to(m)

st.subheader("🗺️ Kaartweergave")
st_folium(m, width=700, height=500)

st.caption("Data: OpenStreetMap x Hugging Face | Tool by Yorbe & Angelo 🚀")
