import requests
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

st.set_page_config(page_title="Scream Zone Finder", layout="wide")
st.title("📣 Vind de dichtstbijzijnde Scream Zone in Antwerpen")

api_key = "AIzaSyCj_pYWMhBRpzZRxtYGziDIr4zYv32_9lA"


@st.cache_data
def load_and_classify():
    dataset = load_dataset("ns2agi/antwerp-osm-navigator")
    df = dataset['train'].to_pandas()
    df = df[['lat', 'lon', 'tags']].dropna()
    df['tags_parsed'] = df['tags'].apply(safe_parse)
    df['label'] = df['tags_parsed'].apply(classify_tags)
    return df[df['label'].str.startswith("✅")].copy()


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


def generate_random_name():
    voornamen = ["Alex", "Sam", "Charlie", "Robin", "Morgan",
                 "Jamie", "Taylor", "Casey", "Jesse", "Riley"]
    achternamen = ["Van Dijk", "Janssens", "Peeters",
                   "De Smet", "Vermeulen", "Claes", "Maes", "Willems"]
    return f"{random.choice(voornamen)} {random.choice(achternamen)}"


if 'user_loc' not in st.session_state:
    st.session_state.user_loc = None

if st.button("📍 Haal mijn locatie op") or st.session_state.user_loc is None:
    location = get_geolocation()
    if location is not None:
        st.session_state.user_loc = (
            location['coords']['latitude'],
            location['coords']['longitude']
        )

if not st.session_state.user_loc:
    st.warning("⏳ Wacht op locatie of klik op de knop hierboven.")
    st.stop()

user_loc = st.session_state.user_loc
st.success(
    f"✅ Je locatie is: {round(user_loc[0], 5)}, {round(user_loc[1], 5)}")

keuze = st.radio("Waar heb je NU nood aan?", [
    "🔎 Toon ALLE scream zones in Antwerpen",
    "📍 Toon ENKEL zones binnen 500 meter"
])

df = load_and_classify()
df['afstand_m'] = df.apply(lambda row: geodesic(
    user_loc, (row['lat'], row['lon'])).meters, axis=1)

if keuze == "📍 Toon ENKEL zones binnen 500 meter":
    filtered_df = df[df['afstand_m'] <= 500].sort_values('afstand_m')
    if filtered_df.empty:
        st.warning(
            "😢 Geen scream zone binnen 500 meter. Misschien even wandelen?")
        st.stop()
    st.subheader("📍 Scream zones binnen 500 meter")
else:
    filtered_df = df.sort_values('afstand_m')
    st.subheader("📍 Alle scream zones in Antwerpen")

m = folium.Map(location=user_loc, zoom_start=14)

folium.Marker(
    location=user_loc,
    popup="🧘 Hier ben jij! ",
    icon=folium.DivIcon(html=f"""<div style='font-size:36px;'>🧘</div>""")
).add_to(m)

# Beperk aantal markers voor performance
max_markers = 200
for _, row in filtered_df.head(max_markers).iterrows():
    lat, lon = row['lat'], row['lon']
    foto_url = "https://source.unsplash.com/300x200/?forest"  # Simpel placeholderbeeld
    popup_html = f"""
    <b>{row['label']}</b><br>
    Afstand: {round(row['afstand_m'])} meter<br>
    <img src="{foto_url}" width="250">
    """
    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(popup_html, max_width=300),
        icon=folium.Icon(color=kleur(row['label']), icon='volume-up')
    ).add_to(m)

# Heatmap beperken tot 1000 punten
heat_data = [[row['lat'], row['lon']] for _, row in df.head(1000).iterrows()]
HeatMap(heat_data, radius=12, blur=15, min_opacity=0.3).add_to(m)

st.subheader("🗺️ Kaartweergave")
st_folium(m, width=700, height=500)

st.caption("Data: OpenStreetMap x Hugging Face | Tool by Yorbe & Angelo 🚀")
