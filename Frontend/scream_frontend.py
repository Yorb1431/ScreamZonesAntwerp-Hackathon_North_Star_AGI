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


@st.cache_data
def load_and_classify():
    dataset = load_dataset("ns2agi/antwerp-osm-navigator")
    df = dataset['train'].to_pandas()
    df = df[['lat', 'lon', 'tags']].dropna()
    df['tags_parsed'] = df['tags'].apply(safe_parse)
    df['label'] = df['tags_parsed'].apply(classify_tags)
    return df[df['label'].str.startswith("✅")].copy()


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
    # ⚠️ Laat alles zien, niet enkel head(5)
    filtered_df = df.sort_values('afstand_m')
    st.subheader("📍 Alle scream zones in Antwerpen")

# 🌍 Kaart genereren
m = folium.Map(location=user_loc, zoom_start=13)

# 🧘 Jij
folium.Marker(
    location=user_loc,
    popup="🧘 Hier ben jij! ",
    icon=folium.DivIcon(html=f"""<div style='font-size:36px;'>🧘</div>""")
).add_to(m)

# 👥 Willekeurige screamers
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

# 📸 Scream zones met foto’s
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

# 🔥 Heatmap
heat_data = [[row['lat'], row['lon']] for _, row in df.iterrows()]
HeatMap(heat_data, radius=12, blur=15, min_opacity=0.3).add_to(m)

st.subheader("🗺️ Kaartweergave")
st_folium(m, width=700, height=500)

st.caption("Data: OpenStreetMap x Hugging Face | Tool by Yorbe & Angelo 🚀")
