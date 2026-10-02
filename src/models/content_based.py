# ============================================================
# Nombre del alumno: Adrián Murillo Moreno
# Descripción: Modelo Content-Based para recomendación de bares
#              usando embeddings semánticos de usuarios y bares.
#              Compatible con el sistema híbrido Switching Hybrid.
# ============================================================

import numpy as np
import pandas as pd


class ContentBasedRecommender:
    def __init__(
        self,
        bars_csv,
        opinions_csv,
        bar_embeddings_path,
        bar_index_path,
        user_embeddings_path,
        user_index_path
    ):
        """
        bars_csv: CSV con información de bares
        opinions_csv: CSV con opiniones finales
        bar_embeddings_path: .npy con embeddings de bares
        bar_index_path: CSV con mapeo placeID -> row_idx
        user_embeddings_path: .npy con embeddings de usuarios
        user_index_path: CSV con mapeo user_id -> row_idx
        """

        # =========================
        # CARGAR DATOS
        # =========================
        self.df_bars = pd.read_csv(bars_csv)
        self.df_opinions = pd.read_csv(opinions_csv)

        self.bar_embeddings = np.load(bar_embeddings_path)
        self.user_embeddings = np.load(user_embeddings_path)

        self.bar_index = pd.read_csv(bar_index_path)
        self.user_index = pd.read_csv(user_index_path)

        # =========================
        # VALIDACIONES MÍNIMAS
        # =========================
        if "placeID" not in self.df_bars.columns:
            raise ValueError("El CSV de bares debe contener la columna 'placeID'.")

        if "placeID" not in self.df_opinions.columns or "user_id" not in self.df_opinions.columns:
            raise ValueError("El CSV de opiniones debe contener 'placeID' y 'user_id'.")

        if "placeID" not in self.bar_index.columns or "row_idx" not in self.bar_index.columns:
            raise ValueError("El índice de bares debe contener 'placeID' y 'row_idx'.")

        if "user_id" not in self.user_index.columns or "row_idx" not in self.user_index.columns:
            raise ValueError("El índice de usuarios debe contener 'user_id' y 'row_idx'.")

        # =========================
        # NORMALIZAR TIPOS
        # =========================
        self.df_bars["placeID"] = pd.to_numeric(self.df_bars["placeID"], errors="coerce")
        self.df_opinions["placeID"] = pd.to_numeric(self.df_opinions["placeID"], errors="coerce")
        self.df_opinions["user_id"] = pd.to_numeric(self.df_opinions["user_id"], errors="coerce")

        self.bar_index["placeID"] = pd.to_numeric(self.bar_index["placeID"], errors="coerce")
        self.bar_index["row_idx"] = pd.to_numeric(self.bar_index["row_idx"], errors="coerce")

        self.user_index["user_id"] = pd.to_numeric(self.user_index["user_id"], errors="coerce")
        self.user_index["row_idx"] = pd.to_numeric(self.user_index["row_idx"], errors="coerce")

        # Eliminar filas inválidas
        self.df_bars = self.df_bars.dropna(subset=["placeID"]).copy()
        self.df_opinions = self.df_opinions.dropna(subset=["placeID", "user_id"]).copy()
        self.bar_index = self.bar_index.dropna(subset=["placeID", "row_idx"]).copy()
        self.user_index = self.user_index.dropna(subset=["user_id", "row_idx"]).copy()

        self.df_bars["placeID"] = self.df_bars["placeID"].astype(int)
        self.df_opinions["placeID"] = self.df_opinions["placeID"].astype(int)
        self.df_opinions["user_id"] = self.df_opinions["user_id"].astype(int)

        self.bar_index["placeID"] = self.bar_index["placeID"].astype(int)
        self.bar_index["row_idx"] = self.bar_index["row_idx"].astype(int)

        self.user_index["user_id"] = self.user_index["user_id"].astype(int)
        self.user_index["row_idx"] = self.user_index["row_idx"].astype(int)

        # =========================
        # FILTRAR ÍNDICES VÁLIDOS
        # =========================
        self.bar_index = self.bar_index[
            (self.bar_index["row_idx"] >= 0) &
            (self.bar_index["row_idx"] < len(self.bar_embeddings))
        ].copy()

        self.user_index = self.user_index[
            (self.user_index["row_idx"] >= 0) &
            (self.user_index["row_idx"] < len(self.user_embeddings))
        ].copy()

        # =========================
        # VALIDAR DIMENSIONES DE EMBEDDINGS
        # =========================
        if len(self.bar_embeddings.shape) != 2 or len(self.user_embeddings.shape) != 2:
            raise ValueError("Las matrices de embeddings deben ser bidimensionales.")

        if self.bar_embeddings.shape[1] != self.user_embeddings.shape[1]:
            raise ValueError(
                "Los embeddings de bares y usuarios deben tener la misma dimensión."
            )

        # =========================
        # DICCIONARIOS DE MAPEADO
        # =========================
        self.item2row = dict(zip(self.bar_index["placeID"], self.bar_index["row_idx"]))
        self.user2row = dict(zip(self.user_index["user_id"], self.user_index["row_idx"]))

        self.all_items = list(self.item2row.keys())

        # =========================
        # HISTORIAL DE USUARIO
        # =========================
        self.user_seen = (
            self.df_opinions.groupby("user_id")["placeID"]
            .apply(set)
            .to_dict()
        )

        # =========================
        # MAPA placeID -> nombre
        # =========================
        if "nombre" in self.df_bars.columns:
            self.placeid_to_name = dict(zip(self.df_bars["placeID"], self.df_bars["nombre"]))
        else:
            self.placeid_to_name = {}

    # =========================
    # SIMILITUD COSENO
    # =========================
    def cosine_scores_dense(self, user_vec, item_matrix, eps=1e-12):
        user_vec = np.asarray(user_vec, dtype=float)
        item_matrix = np.asarray(item_matrix, dtype=float)

        uv = user_vec / (np.linalg.norm(user_vec) + eps)
        im = item_matrix / (np.linalg.norm(item_matrix, axis=1, keepdims=True) + eps)

        return im @ uv

    # =========================
    # OBTENER EMBEDDING DE USUARIO
    # =========================
    def get_user_vector(self, user_id):
        if user_id not in self.user2row:
            return None

        row = int(self.user2row[user_id])

        if row < 0 or row >= len(self.user_embeddings):
            return None

        return self.user_embeddings[row]

    # =========================
    # SCORE DE TODOS LOS ITEMS
    # =========================
    def score_all_items(self, user_id):
        user_vec = self.get_user_vector(user_id)

        if user_vec is None:
            return None

        scores = self.cosine_scores_dense(user_vec, self.bar_embeddings)
        return scores

    # =========================
    # RECOMENDACIÓN TOP-K
    # =========================
    def recommend(self, user_id, k=10, exclude_seen=True):
        scores = self.score_all_items(user_id)

        if scores is None:
            return []

        seen_items = set()
        if exclude_seen:
            seen_items = self.user_seen.get(user_id, set())

        candidates = [item for item in self.all_items if item not in seen_items]

        candidates.sort(
            key=lambda item: scores[int(self.item2row[item])],
            reverse=True
        )

        return candidates[:k]

    # =========================
    # RECOMENDACIÓN TOP-K CON SCORE
    # =========================
    def recommend_with_scores(self, user_id, k=10, exclude_seen=True):
        scores = self.score_all_items(user_id)

        if scores is None:
            return []

        seen_items = set()
        if exclude_seen:
            seen_items = self.user_seen.get(user_id, set())

        candidates = [item for item in self.all_items if item not in seen_items]

        candidates.sort(
            key=lambda item: scores[int(self.item2row[item])],
            reverse=True
        )

        top_items = candidates[:k]

        resultados = []
        for place_id in top_items:
            row_idx = int(self.item2row[place_id])
            resultados.append({
                "placeID": place_id,
                "nombre": self.placeid_to_name.get(place_id, ""),
                "score": float(scores[row_idx])
            })

        return resultados


# ============================================================
# TEST RÁPIDO
# ============================================================

if __name__ == "__main__":

    model = ContentBasedRecommender(
        bars_csv="data/jaen/bares_finales.csv",
        opinions_csv="data/jaen/opiniones.csv",
        bar_embeddings_path="data/jaen/embeddings/embeddings_bares.npy",
        bar_index_path="data/jaen/embeddings/embeddings_index.csv",
        user_embeddings_path="data/jaen/embeddings/user_embeddings.npy",
        user_index_path="data/jaen/embeddings/user_embeddings_index.csv"
    )

    test_user = 9800

    recs = model.recommend_with_scores(test_user, k=10, exclude_seen=True)

    print(f"Recomendaciones CB para usuario {test_user}:")
    for r in recs:
        print(r)