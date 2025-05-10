from datasets import load_dataset
import pandas as pd
import folium

# Stap 1: Laad de dataset van Hugging Face
print("Dataset wordt geladen...")
dataset = load_dataset("ns2agi/antwerp-osm-navigator")
data = dataset['train']
df = data.to_pandas()

# Stap 2: Debug - bekijk voorbeeld 'tags'
non_empty_tags = df[df['tags'].notnull()].head(5)
print("Voorbeeld tags:\n", non_empty_tags[['tags']])

# Stap 3: Probeer scream-vriendelijke locaties (parken) te vinden
def is_park(tag_dict):
    return (
        tag_dict is not None
        and isinstance(tag_dict, dict)
        and tag_dict.get('leisure') == 'park'
    )

print("Filteren op parken...")
parks = df[df['tags'].apply(is_park)]

# Stap 4: Toon resultaten of waarschuwing
if not parks.empty:
    lat, lon = parks.iloc[0]['lat'], parks.iloc[0]['lon']
    m = folium.Map(location=[lat, lon], zoom_start=13)

    for _, row in parks.iterrows():
        folium.Marker(
            location=[row['lat'], row['lon']],
            popup="Scream Zone: Park",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)

    # Opslaan
    m.save("scream_zones_map.html")
    print("Kaart opgeslagen als 'scream_zones_map.html'.")
else:
    print("❌ Geen parken gevonden in de dataset.")
    print("⚠️ Check de tags hierboven om alternatieve scream zones te vinden.")

