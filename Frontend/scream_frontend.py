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
import numpy as np
from numpy import radians, cos, sin, sqrt, arctan2

st.set_page_config(page_title="Scream Zone Finder", layout="wide")
st.title("📣 Vind de dichtstbijzijnde Scream Zone in Antwerpen")

api_key = "AIzaSyCj_pYWMhBRpzZRxtYGziDIr4zYv32_9lA"

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

    disqualifiers = ['building', 'addr:street', 'addr:housenumber', 'highway', 'railway', 'amenity']
    if any(k in tags for k in disqualifiers):
        return "❌ Niet geschikt"

    if tags.get('landuse') in ['industrial', 'railway']:
        return "✅ Industriegebied"
    if tags.get('natural') in ['wood', 'scrub', 'heath', 'grassland']:
        return "✅ Natuurgebied"
    if tags.get('leisure') in ['park', 'nature_reserve']:
        return "✅ Natuurgebied"
    if tags.get('service') in ['alley', 'industrial']:
        return "✅ Afgelegen zone"

    return "⚠️ Onzeker"

def kleur(label):
    if "✅" in label:
        return "green"
    elif "❌" in label:
        return "red"
    else:
        return "orange"

def generate_random_name():
    voornamen = ["Alex", "Sam", "Charlie", "Robin", "Morgan", "Jamie", "Taylor", "Casey", "Jesse", "Riley"]
    achternamen = ["Van Dijk", "Janssens", "Peeters", "De Smet", "Vermeulen", "Claes", "Maes", "Willems"]
    return f"{random.choice(voornamen)} {random.choice(achternamen)}"

def fast_haversine(lat1, lon1, lat2_array, lon2_array):
    R = 6371000  # meters
    lat1_rad, lon1_rad = radians(lat1), radians(lon1)
    lat2_rad, lon2_rad = radians(lat2_array), radians(lon2_array)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = np.sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

@st.cache_data
def load_and_classify():
    dataset = load_dataset("ns2agi/antwerp-osm-navigator")
    df = dataset['train'].to_pandas()
    df = df[['lat', 'lon', 'tags']].dropna()
    df['tags_parsed'] = df['tags'].apply(safe_parse)
    df['label'] = df['tags_parsed'].apply(classify_tags)
    df = df[df['label'].str.startswith("\u2705")].copy()
    df = df.sample(n=min(500, len(df)))
    return df

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
st.success(f"✅ Je locatie is: {round(user_loc[0], 5)}, {round(user_loc[1], 5)}")

df = load_and_classify()
df['afstand_m'] = fast_haversine(user_loc[0], user_loc[1], df['lat'], df['lon'])

st.subheader("🔍 Filteropties")
if 'filter_active' not in st.session_state:
    st.session_state.filter_active = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🧽 Waar kan ik NU schreeuwen?"):
        st.session_state.filter_active = True
with col2:
    if st.button("🔄 Toon alle scream zones"):
        st.session_state.filter_active = False

if st.session_state.filter_active:
    filtered_df = df[df['afstand_m'] <= 500].sort_values('afstand_m')
    st.subheader("📍 Scream zones binnen 500 meter")
    if filtered_df.empty:
        st.warning("😥 Geen scream zone binnen 500 meter. Misschien even wandelen?")
else:
    filtered_df = df.sort_values('afstand_m')
    st.subheader("📍 Alle scream zones in Antwerpen")

m = folium.Map(location=user_loc, zoom_start=13)

folium.Marker(
    location=user_loc,
    popup="🧘 Hier ben jij! ",
    icon=folium.DivIcon(html=f"""<div style='font-size:36px;'>🧘</div>""")
).add_to(m)

other_emojis = ["😎", "👽", "🐸", "🧛", "😱", "🤖", "🧌", "🐡", "👿"]
for _ in range(20):
    rand_lat = random.uniform(51.1800, 51.2600)
    rand_lon = random.uniform(4.3500, 4.4800)
    random_name = generate_random_name()
    folium.Marker(
        location=[rand_lat, rand_lon],
        popup=f"👤 {random_name}!!!",
        icon=folium.DivIcon(
            html=f"""<div style='font-size:24px;'>{random.choice(other_emojis)}</div>""")
    ).add_to(m)

for _, row in filtered_df.iterrows():
    lat, lon = row['lat'], row['lon']
    streetview_url = (
        f"https://maps.googleapis.com/maps/api/streetview"
        f"?size=300x200&location={lat},{lon}&fov=80&heading=70&pitch=0&key={api_key}"
    )
    try:
        response = requests.get(streetview_url, timeout=3)
        if len(response.content) < 1000:
            raise Exception("Onbruikbaar beeld")
        foto_url = streetview_url
    except:
        if "industrie" in row['label'].lower():
            foto_url = "https://source.unsplash.com/300x200/?factory"
        elif "natuur" in row['label'].lower():
            foto_url = "https://source.unsplash.com/300x200/?forest"
        else:
            foto_url = "https://source.unsplash.com/300x200/?quiet"

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

heat_data = [[row['lat'], row['lon']] for _, row in df.iterrows()]
HeatMap(heat_data, radius=12, blur=15, min_opacity=0.3).add_to(m)

st.subheader("🗌 Kaartweergave")
st_folium(m, width=700, height=500)

st.caption("Data: OpenStreetMap x Hugging Face | Tool by Yorbe & Angelo 🚀")
