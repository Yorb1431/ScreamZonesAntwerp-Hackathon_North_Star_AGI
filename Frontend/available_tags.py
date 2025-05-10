from datasets import load_dataset
import pandas as pd
import ast
from collections import Counter

# Stap 1: Dataset lokaal laden
dataset = load_dataset("./antwerp-osm-navigator")
data = dataset['train']
df = data.to_pandas()

# Stap 2: Zorg dat tags correct worden geïnterpreteerd
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

# Stap 3: Verzamel alle unieke keys in de tags
all_keys = df['tags_parsed'].apply(lambda x: list(x.keys()) if isinstance(x, dict) else []).explode()

# Stap 4: Tel welke keys het meest voorkomen
tag_counts = Counter(all_keys)

# Stap 5: Print overzicht
print("\n🧩 Top 20 meest voorkomende tag-keys:")
for tag, count in tag_counts.most_common(20):
    print(f"{tag}: {count}")
