import pandas as pd

from src.models.popularity import build_popularity_ranking, evaluate_popularity

# Ajusta rutas a tu estructura
RATINGS_CSV = "data/jaen/opiniones.csv"
ITEMS_CSV   = "data/jaen/bares_finales.csv"

df_ratings = pd.read_csv(RATINGS_CSV)
df_items = pd.read_csv(ITEMS_CSV)

# Asegura columnas mínimas
needed_r = {"user_id", "est_id", "rating"}
needed_i = {"est_id", "val_media", "num_val"}

if not needed_r.issubset(df_ratings.columns):
    raise ValueError(f"opiniones_filtradas.csv debe tener {needed_r}. Tiene {set(df_ratings.columns)}")

if not needed_i.issubset(df_items.columns):
    raise ValueError(f"bares_jaen.csv debe tener {needed_i}. Tiene {set(df_items.columns)}")

print("=== POPULARIDAD (rating) ===")
rank_rating = build_popularity_ranking(df_items, method="rating")
res_rating = evaluate_popularity(df_ratings, rank_rating, ks=(5, 10, 20))
print(res_rating.to_string(index=False))

print("\n=== POPULARIDAD (wilson) ===")
rank_wilson = build_popularity_ranking(df_items, method="wilson")
res_wilson = evaluate_popularity(df_ratings, rank_wilson, ks=(5, 10, 20))
print(res_wilson.to_string(index=False))