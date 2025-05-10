from datasets import load_dataset
import pandas as pd

# Stap 1: Laad dataset vanaf lokale map
dataset = load_dataset("./antwerp-osm-navigator")
data = dataset['train']
df = data.to_pandas()

# Stap 2: Toon basisinformatie
print("🧾 Kolomnamen:")
print(df.columns)

print("\n📊 Eerste 5 rijen:")
print(df.head())

# Stap 3: Toon unieke waarden per kolom (indien aanwezig)
if 'type' in df.columns:
    print("\n📁 Unieke waardes in 'type':")
    print(df['type'].value_counts())

if 'tags' in df.columns:
    print("\n🔖 Eerste 10 unieke niet-lege 'tags':")
    print(df['tags'].dropna().unique()[:10])
