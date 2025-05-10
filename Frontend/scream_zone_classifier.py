from datasets import load_dataset
import pandas as pd
import folium
import ast

# === 1. Laad dataset lokaal ===
dataset = load_dataset("./antwerp-osm-navigator")
data = dataset['train']
df = data.to_pandas()

# === 2. Parse de tags (soms zijn ze strings) ===
def safe_parse(tag):
    if isinstance(tag, dict):
        return tag
    if isinstance(tag, str) and tag.startswith('{'):
        try:
            return ast.literal_eval(tag)
        except:
            return {}
    return {}

df['tags_parsed'] = df['tags'].apply(safe_parse)

# === 3. Classificeer elke locatie ===
def classify_tags(tags):
    if not tags or tags == {}:
        return "⚠️ Onzeker"

    if 'building' in tags or 'addr:street' in tags or 'addr:housenumber' in tags:
        return "❌ Niet geschikt (bebouwd)"

    if 'highway' in tags or 'railway' in tags or 'amenity' in tags:
        return "❌ Niet geschikt (verkeer/voorzieningen)"

    if tags.get('landuse') == 'industrial':
        return "✅ Scream Zone (industriegebied)"

    if tags.get('natural') in ['wood', 'scrub', 'heath']:
        return "✅ Scream Zone (natuurgebied)"

    if tags.get('service') in ['alley', 'industrial']:
        return "✅ Scream Zone (afgelegen)"

    if not any(k in tags for k in ['building', 'addr:street', 'highway', 'railway', 'amenity']):
        return "✅ Rustige plek (geen drukte zichtbaar)"

    return "⚠️ Onzeker"


df['scream_label'] = df['tags_parsed'].apply(classify_tags)

# === 4. Kleurcode voor kaart ===
def kleur(label):
    if "✅" in label:
        return "green"
    elif "❌" in label:
        return "red"
    else:
        return "orange"

# === 5. Toon eerste 100 geclassificeerde locaties op kaart ===
map_df = df[['lat', 'lon', 'scream_label']].dropna().head(100)

m = folium.Map(location=[map_df['lat'].mean(), map_df['lon'].mean()], zoom_start=13)

for _, row in map_df.iterrows():
    folium.Marker(
        location=[row['lat'], row['lon']],
        popup=row['scream_label'],
        icon=folium.Icon(color=kleur(row['scream_label']), icon='volume-up')
    ).add_to(m)

from geopy.distance import geodesic

# Bijvoorbeeld: gebruiker staat bij Antwerpen Centraal
user_location = (51.2175, 4.4214)

# Filter op alleen geschikte zones
suitable = df[df['scream_label'].str.startswith("✅")].copy()

# Bereken afstand
suitable['afstand_m'] = suitable.apply(
    lambda row: geodesic(user_location, (row['lat'], row['lon'])).meters,
    axis=1
)

# Toon de 3 dichtstbijzijnde
print("📍 Dichtstbijzijnde scream zones:")
print(suitable.sort_values('afstand_m')[['lat', 'lon', 'scream_label', 'afstand_m']].head(3))


m.save("classified_scream_zones_map.html")
print("✅ Kaart opgeslagen als 'classified_scream_zones_map.html'")
