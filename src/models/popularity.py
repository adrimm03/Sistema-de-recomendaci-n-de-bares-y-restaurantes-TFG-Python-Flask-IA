import numpy as np
import pandas as pd
from typing import Dict, List, Tuple


def recall_at_k(ranked_items: List[int], target_item: int, k: int) -> float:
    return 1.0 if target_item in ranked_items[:k] else 0.0


def ndcg_at_k(ranked_items: List[int], target_item: int, k: int) -> float:
    if target_item in ranked_items[:k]:
        rank = ranked_items.index(target_item) + 1
        return 1.0 / np.log2(rank + 1)
    return 0.0


def build_positives_by_user_jaen(df_ratings: pd.DataFrame) -> Dict[int, List[int]]:
    """
    Espera columnas: user_id, est_id, rating
    Positivo si rating >= 4
    """
    df = df_ratings.copy()
    df["y"] = (df["rating"] >= 4.0).astype(int)
    pos = (
        df[df["y"] == 1]
        .groupby("user_id")["est_id"]
        .apply(list)
        .to_dict()
    )
    return pos


def leave_one_out_splits(pos_by_user: Dict[int, List[int]]) -> List[Tuple[int, List[int], int]]:
    """
    (user_id, train_items, test_item) para usuarios con >=2 positivos.
    test_item = último elemento (si quieres por fecha, ordena antes en df_ratings).
    """
    splits = []
    for u, items in pos_by_user.items():
        if len(items) < 2:
            continue
        test_item = items[-1]
        train_items = items[:-1]
        splits.append((u, train_items, test_item))
    return splits


def wilson_lower_bound(p: float, n: float, z: float = 1.96) -> float:
    """
    Wilson score lower bound para proporciones.
    Aquí adaptamos rating (1..5) a proporción 0..1.
    """
    if n <= 0:
        return 0.0
    denom = 1 + z**2 / n
    center = p + z**2 / (2*n)
    margin = z * np.sqrt((p*(1-p) + z**2/(4*n)) / n)
    return (center - margin) / denom


def build_popularity_ranking(
    df_items: pd.DataFrame,
    method: str = "rating",
    min_votes: int = 1
) -> List[int]:
    """
    df_items espera: est_id, val_media, num_val
    method:
      - "rating": ordenar por val_media desc, luego num_val desc
      - "wilson": usar wilson lower bound (rating normalizado) con num_val
    """
    items = df_items[["est_id", "val_media", "num_val"]].copy()
    items["est_id"] = pd.to_numeric(items["est_id"], errors="coerce").astype(int)
    items["val_media"] = pd.to_numeric(items["val_media"], errors="coerce")
    items["num_val"] = pd.to_numeric(items["num_val"], errors="coerce").fillna(0).astype(int)

    items = items[items["num_val"] >= min_votes].copy()

    if method == "rating":
        items = items.sort_values(["val_media", "num_val"], ascending=[False, False])
        return items["est_id"].tolist()

    if method == "wilson":
        # normaliza rating 1..5 -> 0..1
        p = (items["val_media"].clip(1, 5) - 1) / 4
        n = items["num_val"].astype(float)
        items["wilson"] = [wilson_lower_bound(pi, ni) for pi, ni in zip(p, n)]
        items = items.sort_values(["wilson", "num_val"], ascending=[False, False])
        return items["est_id"].tolist()

    raise ValueError("method debe ser 'rating' o 'wilson'")


def evaluate_popularity(
    df_ratings: pd.DataFrame,
    pop_ranking: List[int],
    ks=(5, 10, 20)
) -> pd.DataFrame:
    """
    Evaluación Leave-One-Out:
    - Para cada usuario: ocultamos 1 positivo (test)
    - Recomendamos top-K entre items NO vistos en train
    """
    pos = build_positives_by_user_jaen(df_ratings)
    splits = leave_one_out_splits(pos)

    results = []
    for k in ks:
        recalls, ndcgs = [], []
        for u, train_items, test_item in splits:
            seen_train = set(train_items)

            # candidatos = ranking global quitando vistos de train
            ranked = [i for i in pop_ranking if i not in seen_train][:k]

            recalls.append(recall_at_k(ranked, test_item, k))
            ndcgs.append(ndcg_at_k(ranked, test_item, k))

        results.append({
            "K": k,
            "users_evaluated": len(splits),
            "Recall@K": float(np.mean(recalls)) if recalls else 0.0,
            "NDCG@K": float(np.mean(ndcgs)) if ndcgs else 0.0
        })

    return pd.DataFrame(results)