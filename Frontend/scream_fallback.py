from datasets import load_dataset
import pandas as pd
import folium
import random

# 1. Dataset lokaal laden
dataset = load_dataset("./antwerp-osm-navigator")
data = dataset['train']
df = data.to_pandas()

# 2. Coördinaten opschonen
df = df[['lat', 'lon']].dropna().drop_duplicates()

# 3. Kies willekeurige gespreide scream zones (max 50)
scream_candidates = df.sample(n=min(50, len(df)), random_state=42)

# 4. Interactieve kaart maken
if not scream_candidates.empty:
    lat, lon = scream_candidates.iloc[0]['lat'], scream_candidates.iloc[0]['lon']
    m = folium.Map(location=[lat, lon], zoom_start=13)

    for _, row in scream_candidates.iterrows():
        folium.Marker(
            location=[row['lat'], row['lon']],
            popup="Potentiële Scream Zone 📢",
            icon=folium.Icon(color='purple', icon='volume-up')
        ).add_to(m)

    m.save("fallback_scream_zones_map.html")
    print("✅ Kaart opgeslagen als 'fallback_scream_zones_map.html'")
else:
    print("⚠️ Geen bruikbare locaties gevonden.")
