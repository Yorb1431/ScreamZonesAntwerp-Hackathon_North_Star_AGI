import streamlit as st
import pandas as pd
import folium
from geopy.distance import geodesic
from datasets import load_dataset
import ast
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation

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

# 1. Automatisch gebruikerlocatie ophalen
location = get_geolocation()

if location is None:
    st.warning("📍 Je locatie wordt opgehaald... Sta het toe in je browser.")
    st.stop()

lat = location['coords']['latitude']
lon = location['coords']['longitude']
user_loc = (lat, lon)

st.success(f"✅ Je locatie is: {round(lat, 5)}, {round(lon, 5)}")

# 2. Laad dataset & classificeer scream zones
df = load_and_classify()

# 3. Bereken afstand tot gebruiker
df['afstand_m'] = df.apply(lambda row: geodesic(
    user_loc, (row['lat'], row['lon'])).meters, axis=1)

# 4. Voeg knop toe voor filtering
st.subheader("🔎 Zoek scream zones")

if 'filter_active' not in st.session_state:
    st.session_state.filter_active = False

if st.button("🧭 Waar kan ik NU schreeuwen?"):
    st.session_state.filter_active = True

if st.button("🔄 Toon alle scream zones"):
    st.session_state.filter_active = False

# 5. Filter dataset op basis van selectie
if st.session_state.filter_active:
    filtered_df = df[df['afstand_m'] <= 500].sort_values('afstand_m')
    st.subheader("📍 Scream zones binnen 500 meter")
    if filtered_df.empty:
        st.warning(
            "😢 Geen scream zone binnen 500 meter. Misschien even wandelen?")
else:
    filtered_df = df.sort_values('afstand_m').head(5)
    st.subheader("📍 Dichtstbijzijnde scream zones")

# 6. Teken kaart
m = folium.Map(location=user_loc, zoom_start=14)
folium.Marker(location=user_loc, popup="📍 Jouw locatie",
              icon=folium.Icon(color="blue")).add_to(m)

for _, row in filtered_df.iterrows():
    folium.Marker(
        location=[row['lat'], row['lon']],
        popup=f"{row['label']} ({round(row['afstand_m'])} m)",
        icon=folium.Icon(color=kleur(row['label']), icon='volume-up')
    ).add_to(m)

st_folium(m, width=700, height=500)
