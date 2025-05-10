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

# ✅ MOET HIER KOMEN
st.set_page_config(page_title="Scream Zone Finder", layout="wide")

st.title("📣 Vind de dichtstbijzijnde Scream Zone in Antwerpen")

# 🔑 VUL HIER JOUW GOOGLE API KEY IN
api_key = "AIzaSyCj_pYWMhBRpzZRxtYGziDIr4zYv32_9lA"

# =========  HELPERS  =========================================================


def safe_parse(tag):
    if isinstance(tag, dict):
        return tag
    if isinstance(tag, str) and tag.startswith('{'):
        try:
            return ast.literal_eval(tag)
        except Exception:
            return {}
    return {}


def classify_tags(tags):
    """Translate raw OSM tags → simple labels."""
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


def kleur(label_or_rating):
    """Green for good, orange for meh, red for avoid."""
    if isinstance(label_or_rating, str) and "✅" in label_or_rating:
        return "green"
    if isinstance(label_or_rating, str) and ("🔊🔊🔊🔊🔊" in label_or_rating or "🔊🔊🔊🔊" in label_or_rating):
        return "green"
    if "❌" in label_or_rating or "🔇" in label_or_rating:
        return "red"
    return "orange"


def generate_random_name():
    voornamen = ["Alex", "Sam", "Charlie", "Robin", "Morgan",
                 "Jamie", "Taylor", "Casey", "Jesse", "Riley"]
    achternamen = ["Van Dijk", "Janssens", "Peeters",
                   "De Smet", "Vermeulen", "Claes", "Maes", "Willems"]
    return f"{random.choice(voornamen)} {random.choice(achternamen)}"


@st.cache_data(show_spinner="🛰️ OSM-data laden…")
def load_and_classify():
    dataset = load_dataset("ns2agi/antwerp-osm-navigator")
    df = dataset['train'].to_pandas()
    df = df[['lat', 'lon', 'tags']].dropna()
    df['tags_parsed'] = df['tags'].apply(safe_parse)
    df['label'] = df['tags_parsed'].apply(classify_tags)
    return df[df['label'].str.startswith("✅")].copy()


# =========  USER LOCATION  ===================================================

if 'user_loc' not in st.session_state:
    location = get_geolocation()
    if location is None:
        st.warning("📍 Je locatie wordt opgehaald... Sta het toe in je browser.")
        st.stop()
    st.session_state.user_loc = (
        location['coords']['latitude'],
        location['coords']['longitude']
    )

user_loc = st.session_state.user_loc
st.success(
    f"✅ Je locatie is: {round(user_loc[0], 5)}, {round(user_loc[1], 5)}")

# =========  CORE DATA  =======================================================

df = load_and_classify()
df['afstand_m'] = df.apply(lambda row: geodesic(user_loc, (row['lat'], row['lon'])).meters,
                           axis=1)

# =========  FILTER UI  =======================================================

st.subheader("🔍 Filteropties")
if 'filter_active' not in st.session_state:
    st.session_state.filter_active = False

c1, c2 = st.columns(2)
with c1:
    if st.button("🧭 Waar kan ik NU schreeuwen?"):
        st.session_state.filter_active = True
with c2:
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

# =========  MAP  ============================================================

m = folium.Map(location=user_loc, zoom_start=14, control_scale=True)

# 🧘 Jij
folium.Marker(
    location=user_loc,
    popup="🧘 Hier ben jij!",
    icon=folium.DivIcon(html="<div style='font-size:36px;'>🧘</div>")
).add_to(m)

# 👥 Willekeurige screamers
other_emojis = ["😎", "👽", "🐸", "🧛", "😱", "🤖", "🧌", "🐡", "👿"]
for _ in range(20):
    rand_lat = random.uniform(51.1800, 51.2600)
    rand_lon = random.uniform(4.3500, 4.4800)
    folium.Marker(
        location=[rand_lat, rand_lon],
        popup=f"👤 {generate_random_name()}!!!",
        icon=folium.DivIcon(
            html=f"<div style='font-size:24px;'>{random.choice(other_emojis)}</div>")
    ).add_to(m)

# =========  EXISTING DATA MARKERS  ==========================================

for _, row in filtered_df.iterrows():
    lat, lon = row['lat'], row['lon']
    streetview_url = (
        f"https://maps.googleapis.com/maps/api/streetview"
        f"?size=300x200&location={lat},{lon}&fov=80&heading=70&pitch=0&key={api_key}"
    )

    try:
        response = requests.get(streetview_url, timeout=3)
        if len(response.content) < 1000:
            raise ValueError("Onbruikbaar beeld")
        foto_url = streetview_url
    except Exception:
        if "industrie" in row['label'].lower():
            foto_url = "https://source.unsplash.com/300x200/?factory"
        elif "natuur" in row['label'].lower():
            foto_url = "https://source.unsplash.com/300x200/?forest"
        else:
            foto_url = "https://source.unsplash.com/300x200/?quiet"

    popup_html = f"""
    <b>{row['label']}</b><br>
    Afstand: {round(row['afstand_m'])} m<br>
    <img src="{foto_url}" width="250">
    """

    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(popup_html, max_width=300),
        icon=folium.Icon(color=kleur(row['label']), icon='volume-up')
    ).add_to(m)

# =========  🎲  RANDOM SCREAM-ZONES  ========================================

# Master spec → details for each zone type
ZONE_SPECS = {
    "Forest":       {"emoji": "🌲", "acoustics": "High Echo & Isolated",     "safety": "✅ Safe",    "rating": "🔊🔊🔊🔊🔊"},
    "Tunnel":       {"emoji": "🎤", "acoustics": "Max Echo",                "safety": "⚠️ Sketchy", "rating": "🔊🔊🔊🔊"},
    "Park":         {"emoji": "🌳", "acoustics": "Medium Echo & Visible",   "safety": "✅ Okay",    "rating": "🔊🔊🔊"},
    "Public Square": {"emoji": "🚫", "acoustics": "Loud but risky",          "safety": "❌ Avoid",   "rating": "🔇"},
    "Riverbank":    {"emoji": "🌊", "acoustics": "Melancholic Scream Vibes", "safety": "✅ Peaceful", "rating": "🔊🔊🔊🔊"},
    "Alley":        {"emoji": "🤫", "acoustics": "Echo but scary",          "safety": "⚠️ Not Ideal", "rating": "🔊🔊"},
}

st.divider()
st.subheader("🥳 Experimentele random scream-zones in Antwerpen")

NUM_RANDOM_ZONES = 60
for _ in range(NUM_RANDOM_ZONES):
    z_type = random.choice(list(ZONE_SPECS.keys()))
    spec = ZONE_SPECS[z_type]
    rand_lat = random.uniform(51.1800, 51.2600)
    rand_lon = random.uniform(4.3500, 4.4800)

    popup_html = f"""
    <b>{spec['emoji']} {z_type}</b><br>
    Acoustics: {spec['acoustics']}<br>
    Safety: {spec['safety']}<br>
    Rating: {spec['rating']}
    """

    # Colour by rating/severity
    marker_color = kleur(spec['rating'])

    folium.Marker(
        location=[rand_lat, rand_lon],
        popup=folium.Popup(popup_html, max_width=250),
        icon=folium.DivIcon(
            html=f"<div style='font-size:24px;'>{spec['emoji']}</div>")
    ).add_to(m)

# =========  HEATMAP  ========================================================

heat_data = [[row['lat'], row['lon']] for _, row in df.iterrows()]
HeatMap(heat_data, radius=12, blur=15, min_opacity=0.3).add_to(m)

st.subheader("🗺️ Kaartweergave")
st_folium(m, width=700, height=500)

st.caption("Data: OpenStreetMap × Hugging Face | Tool by Yorbe & Angelo 🚀")

# =========  SUGGEST FORM  ====================================================

st.subheader("📬 Stel een nieuwe scream zone voor")

with st.form("scream_form"):
    naam = st.text_input("Jouw naam (optioneel)", "")
    lat_input = st.number_input("Breedtegraad (lat)", format="%.6f")
    lon_input = st.number_input("Lengtegraad (lon)", format="%.6f")
    zone_type = st.selectbox(
        "Type zone", ["Rustig", "Natuurgebied", "Industrie", "Anders"])
    opmerking = st.text_area(
        "Waarom is dit een goeie plek om te schreeuwen?", "")
    verzenden = st.form_submit_button("✅ Verstuur")

    if verzenden:
        nieuw = pd.DataFrame([{
            "naam": naam or "🕵️ Anoniem",
            "lat": lat_input,
            "lon": lon_input,
            "type": zone_type,
            "opmerking": opmerking
        }])

        try:
            bestandsnaam = "suggested_zones.csv"
            nieuw.to_csv(bestandsnaam, mode='a',
                         header=not pd.io.common.file_exists(bestandsnaam),
                         index=False)
            st.success("Bedankt voor je suggestie! 🎉")
        except Exception as e:
            st.error(f"Er ging iets mis bij het opslaan: {e}")

if pd.io.common.file_exists("suggested_zones.csv"):
    st.markdown("### 📄 Ingestuurde scream zones")
    suggesties = pd.read_csv("suggested_zones.csv")
    st.dataframe(suggesties)
