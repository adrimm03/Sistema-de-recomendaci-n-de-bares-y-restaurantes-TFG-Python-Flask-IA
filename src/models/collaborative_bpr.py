# ============================================================
# Nombre del alumno: Adrián Murillo Moreno
# Descripción: Modelo colaborativo basado en BPR (Cornac)
#              para recomendar bares a partir de interacciones
#              positivas de usuarios similares.
# ============================================================

import random
import numpy as np
import pandas as pd
import cornac
from cornac.models import BPR

# =========================
# SEMILLA GLOBAL
# =========================

SEED = 42
random.seed(SEED)
np.random.seed(SEED)


class CollaborativeBPR:
    def __init__(self, k=50, max_iter=100, learning_rate=0.01, lambda_reg=0.01):
        self.k = k
        self.max_iter = max_iter
        self.learning_rate = learning_rate
        self.lambda_reg = lambda_reg

        self.model = None
        self.dataset = None
        self.train_df = None
        self.df_bars = None
        self.placeid_to_name = {}

    # =========================
    # PREPARAR DATOS
    # =========================
    def preparar_datos(self, opinions_csv):
        df = pd.read_csv(opinions_csv)

        columnas_necesarias = {"user_id", "placeID", "rating"}
        if not columnas_necesarias.issubset(df.columns):
            raise ValueError(
                f"El CSV de opiniones debe contener {columnas_necesarias}. "
                f"Columnas actuales: {list(df.columns)}"
            )

        # Normalizar tipos
        df["user_id"] = pd.to_numeric(df["user_id"], errors="coerce")
        df["placeID"] = pd.to_numeric(df["placeID"], errors="coerce")
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

        # Eliminar filas inválidas
        df = df.dropna(subset=["user_id", "placeID", "rating"]).copy()

        df["user_id"] = df["user_id"].astype(int)
        df["placeID"] = df["placeID"].astype(int)

        # Solo interacciones positivas
        df = df[df["rating"] >= 4].copy()

        # Orden estable
        df = df.sort_values(["user_id", "placeID"]).reset_index(drop=True)

        # Eliminar duplicados exactos usuario-item
        df = df.drop_duplicates(subset=["user_id", "placeID"])

        if df.empty:
            raise ValueError("No hay interacciones positivas válidas para entrenar BPR.")

        self.train_df = df.copy()

        # Formato Cornac: (usuario, item, interacción)
        data = list(zip(df["user_id"], df["placeID"], [1] * len(df)))

        return data

    # =========================
    # CARGAR BARES
    # =========================
    def cargar_bares(self, bars_csv):
        df_bars = pd.read_csv(bars_csv)

        if "placeID" not in df_bars.columns:
            raise ValueError("El CSV de bares debe contener la columna 'placeID'.")

        df_bars["placeID"] = pd.to_numeric(df_bars["placeID"], errors="coerce")
        df_bars = df_bars.dropna(subset=["placeID"]).copy()
        df_bars["placeID"] = df_bars["placeID"].astype(int)

        self.df_bars = df_bars

        if "nombre" in df_bars.columns:
            self.placeid_to_name = dict(zip(df_bars["placeID"], df_bars["nombre"]))
        else:
            self.placeid_to_name = {}

    # =========================
    # ENTRENAR
    # =========================
    def fit(self, opinions_csv, bars_csv=None):
        print("Preparando datos BPR...")
        data = self.preparar_datos(opinions_csv)

        if bars_csv is not None:
            self.cargar_bares(bars_csv)

        print("Entrenando modelo BPR...")
        self.dataset = cornac.data.Dataset.from_uir(data)

        self.model = BPR(
            k=self.k,
            max_iter=self.max_iter,
            learning_rate=self.learning_rate,
            lambda_reg=self.lambda_reg,
            seed=SEED,
            verbose=True
        )

        self.model.fit(self.dataset)
        print("Modelo entrenado correctamente")

    # =========================
    # SCORE TODOS LOS ITEMS
    # =========================
    def score_all_items(self, user_id):
        if self.model is None or self.dataset is None:
            raise Exception("Modelo no entrenado")

        try:
            uidx = self.dataset.uid_map[user_id]
        except KeyError:
            return None

        scores = self.model.score(uidx)
        return scores

    # =========================
    # RECOMENDACIONES TOP-K
    # =========================
    def recommend(self, user_id, k=10, exclude_seen=True):
        scores = self.score_all_items(user_id)

        if scores is None:
            return []

        id_map = self.dataset.iid_map
        inv_map = {v: k for k, v in id_map.items()}

        ranked_idx = np.argsort(scores)[::-1]

        recomendaciones = []

        seen_items = set()
        if exclude_seen and self.train_df is not None:
            seen_items = set(
                self.train_df[self.train_df["user_id"] == user_id]["placeID"].tolist()
            )

        for idx in ranked_idx:
            place_id = inv_map[idx]

            if exclude_seen and place_id in seen_items:
                continue

            recomendaciones.append(place_id)

            if len(recomendaciones) == k:
                break

        return recomendaciones

    # =========================
    # RECOMENDACIONES TOP-K CON SCORE
    # =========================
    def recommend_with_scores(self, user_id, k=10, exclude_seen=True):
        scores = self.score_all_items(user_id)

        if scores is None:
            return []

        id_map = self.dataset.iid_map
        inv_map = {v: k for k, v in id_map.items()}

        ranked_idx = np.argsort(scores)[::-1]

        resultados = []

        seen_items = set()
        if exclude_seen and self.train_df is not None:
            seen_items = set(
                self.train_df[self.train_df["user_id"] == user_id]["placeID"].tolist()
            )

        for idx in ranked_idx:
            place_id = inv_map[idx]

            if exclude_seen and place_id in seen_items:
                continue

            resultados.append({
                "placeID": place_id,
                "nombre": self.placeid_to_name.get(place_id, ""),
                "score": float(scores[idx])
            })

            if len(resultados) == k:
                break

        return resultados


if __name__ == "__main__":
    PATH_OPINIONES = "data/jaen/opiniones.csv"
    PATH_BARES = "data/jaen/bares_finales.csv"

    model = CollaborativeBPR(
        k=50,
        max_iter=100,
        learning_rate=0.01,
        lambda_reg=0.01
    )

    model.fit(PATH_OPINIONES, bars_csv=PATH_BARES)

    test_user = 9800
    recs = model.recommend_with_scores(test_user, k=10, exclude_seen=True)

    print(f"Recomendaciones colaborativas para usuario {test_user}:")
    for r in recs:
        print(r)

