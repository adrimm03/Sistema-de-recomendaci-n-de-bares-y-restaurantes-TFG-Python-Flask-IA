# ============================================================
# Nombre del alumno: Adrián Murillo Moreno
# Descripción: Sistema híbrido para recomendación de bares.
#              - Si el usuario no tiene interacciones:
#                    no hay recomendaciones
#              - Si tiene entre 1 y 4 interacciones:
#                    usa solo Content-Based
#              - Si tiene entre 5 y 6 interacciones:
#                    usa híbrido 50% colaborativo + 50% contenido
#              - Si tiene entre 7 y 14 interacciones:
#                    usa híbrido 60% colaborativo + 40% contenido
#              - Si tiene 15 o más interacciones:
#                    usa híbrido 70% colaborativo + 30% contenido
# ============================================================

import numpy as np
import pandas as pd


class HybridRecommender:
    def __init__(self, content_model, collaborative_model, usuarios_csv):
        """
        content_model: instancia de ContentBasedRecommender
        collaborative_model: instancia de CollaborativeBPR
        usuarios_csv: ruta a usuarios_finales.csv
        """
        self.content_model = content_model
        self.collaborative_model = collaborative_model

        self.df_users = pd.read_csv(usuarios_csv)

        # =========================
        # VALIDACIONES Y NORMALIZACIÓN
        # =========================
        if "user_id" not in self.df_users.columns:
            raise ValueError("El CSV de usuarios debe contener la columna 'user_id'.")

        if "n_interacciones" not in self.df_users.columns:
            raise ValueError("El CSV de usuarios debe contener la columna 'n_interacciones'.")

        self.df_users["user_id"] = pd.to_numeric(self.df_users["user_id"], errors="coerce")
        self.df_users["n_interacciones"] = pd.to_numeric(
            self.df_users["n_interacciones"], errors="coerce"
        ).fillna(0)

        self.df_users = self.df_users.dropna(subset=["user_id"]).copy()
        self.df_users["user_id"] = self.df_users["user_id"].astype(int)
        self.df_users["n_interacciones"] = self.df_users["n_interacciones"].astype(int)

        # Diccionario user_id -> número de interacciones
        self.user_interactions = dict(
            zip(self.df_users["user_id"], self.df_users["n_interacciones"])
        )

    # =========================
    # OBTENER Nº INTERACCIONES
    # =========================
    def get_user_interactions(self, user_id):
        return int(self.user_interactions.get(user_id, 0))

    # =========================
    # ELEGIR ESTRATEGIA
    # =========================
    def choose_strategy(self, user_id):
        n_inter = self.get_user_interactions(user_id)

        if n_inter == 0:
            return "none"

        if 1 <= n_inter <= 4:
            return "content_only"

        return "weighted_hybrid"

    # =========================
    # OBTENER PESOS DEL HÍBRIDO
    # =========================
    def get_hybrid_weights(self, user_id):
        n_inter = self.get_user_interactions(user_id)

        if 5 <= n_inter <= 6:
            return 0.5, 0.5

        if 7 <= n_inter <= 14:
            return 0.6, 0.4

        if n_inter >= 15:
            return 0.7, 0.3

        return None, None

    # =========================
    # NORMALIZAR VECTOR DE SCORES
    # =========================
    def normalize_array(self, arr):
        arr = np.asarray(arr, dtype=float)

        if arr.size == 0:
            return arr

        min_val = np.min(arr)
        max_val = np.max(arr)

        if max_val == min_val:
            return np.ones_like(arr, dtype=float)

        return (arr - min_val) / (max_val - min_val)

    # =========================
    # OBTENER BARES VISTOS
    # =========================
    def get_seen_items(self, user_id):
        seen_cb = self.content_model.user_seen.get(user_id, set())

        seen_bpr = set()
        if self.collaborative_model.train_df is not None:
            seen_bpr = set(
                self.collaborative_model.train_df[
                    self.collaborative_model.train_df["user_id"] == user_id
                ]["placeID"].tolist()
            )

        return set(seen_cb) | set(seen_bpr)

    # =========================
    # RECOMENDAR
    # =========================
    def recommend(self, user_id, k=10, exclude_seen=True):
        strategy = self.choose_strategy(user_id)
        n_inter = self.get_user_interactions(user_id)

        # ------------------------------------------------
        # CASO 1: SIN INTERACCIONES
        # ------------------------------------------------
        if strategy == "none":
            return {
                "user_id": user_id,
                "n_interacciones": n_inter,
                "estrategia": strategy,
                "mensaje": "No hay recomendaciones para este usuario",
                "recomendaciones": []
            }

        # ------------------------------------------------
        # CASO 2: POCAS INTERACCIONES -> SOLO CONTENT-BASED
        # ------------------------------------------------
        if strategy == "content_only":
            recs_cb = self.content_model.recommend_with_scores(
                user_id=user_id,
                k=k,
                exclude_seen=exclude_seen
            )

            mensaje = (
                f"Se usa solo el modelo Content-Based para recomendar {len(recs_cb)} bares "
                f"porque el usuario tiene entre 1 y 4 interacciones ({n_inter})."
            )

            return {
                "user_id": user_id,
                "n_interacciones": n_inter,
                "estrategia": strategy,
                "mensaje": mensaje,
                "recomendaciones": recs_cb
            }

        # ------------------------------------------------
        # CASO 3: HÍBRIDO PONDERADO
        # ------------------------------------------------
        peso_bpr, peso_cb = self.get_hybrid_weights(user_id)

        if peso_bpr is None or peso_cb is None:
            return {
                "user_id": user_id,
                "n_interacciones": n_inter,
                "estrategia": "none",
                "mensaje": "No se pudo determinar la estrategia híbrida.",
                "recomendaciones": []
            }

        # Scores reales de todos los items
        scores_cb = self.content_model.score_all_items(user_id)
        scores_bpr = self.collaborative_model.score_all_items(user_id)

        # Si alguno falla, degradar de forma controlada
        if scores_cb is None and scores_bpr is None:
            return {
                "user_id": user_id,
                "n_interacciones": n_inter,
                "estrategia": strategy,
                "mensaje": "No hay recomendaciones para este usuario",
                "recomendaciones": []
            }

        if scores_cb is None:
            recs_bpr = self.collaborative_model.recommend_with_scores(
                user_id=user_id,
                k=k,
                exclude_seen=exclude_seen
            )
            return {
                "user_id": user_id,
                "n_interacciones": n_inter,
                "estrategia": "collaborative_only_fallback",
                "mensaje": (
                    "Se usa solo el modelo colaborativo porque no se pudo obtener "
                    "el score del modelo basado en contenido para este usuario."
                ),
                "recomendaciones": recs_bpr
            }

        if scores_bpr is None:
            recs_cb = self.content_model.recommend_with_scores(
                user_id=user_id,
                k=k,
                exclude_seen=exclude_seen
            )
            return {
                "user_id": user_id,
                "n_interacciones": n_inter,
                "estrategia": "content_only_fallback",
                "mensaje": (
                    "Se usa solo el modelo Content-Based porque no se pudo obtener "
                    "el score del modelo colaborativo para este usuario."
                ),
                "recomendaciones": recs_cb
            }

        # Obtener universo común de items que el content model puede mapear
        all_place_ids = list(self.content_model.all_items)

        # Normalizar scores completos
        scores_cb_norm = self.normalize_array(scores_cb)
        scores_bpr_norm = self.normalize_array(scores_bpr)

        # Mapear placeID -> score real normalizado
        cb_score_by_place = {}
        for place_id in all_place_ids:
            row_idx = int(self.content_model.item2row[place_id])
            cb_score_by_place[place_id] = float(scores_cb_norm[row_idx])

        bpr_score_by_place = {}
        inv_bpr_map = {v: k for k, v in self.collaborative_model.dataset.iid_map.items()}

        for internal_idx, place_id in inv_bpr_map.items():
            bpr_score_by_place[place_id] = float(scores_bpr_norm[internal_idx])

        # Bares vistos por el usuario
        seen_items = set()
        if exclude_seen:
            seen_items = self.get_seen_items(user_id)

        # Construir resultados finales
        resultados = []
        for place_id in all_place_ids:
            if exclude_seen and place_id in seen_items:
                continue

            score_cb = cb_score_by_place.get(place_id, 0.0)
            score_bpr = bpr_score_by_place.get(place_id, 0.0)

            score_final = peso_bpr * score_bpr + peso_cb * score_cb

            resultados.append({
                "placeID": place_id,
                "nombre": self.content_model.placeid_to_name.get(place_id, ""),
                "score_cb": float(score_cb),
                "score_bpr": float(score_bpr),
                "score_final": float(score_final)
            })

        resultados.sort(key=lambda x: x["score_final"], reverse=True)
        resultados = resultados[:k]

        mensaje = (
            f"Se usan ambos modelos porque el usuario tiene {n_inter} interacciones. "
            f"El score final se calcula como {peso_bpr:.1f} * modelo colaborativo + "
            f"{peso_cb:.1f} * modelo basado en contenido, usando los scores reales "
            f"de ambos modelos para cada bar candidato."
        )

        return {
            "user_id": user_id,
            "n_interacciones": n_inter,
            "estrategia": strategy,
            "peso_bpr": peso_bpr,
            "peso_cb": peso_cb,
            "mensaje": mensaje,
            "recomendaciones": resultados
        }


# ============================================================
# TEST RÁPIDO
# ============================================================

if __name__ == "__main__":
    from content_based import ContentBasedRecommender
    from collaborative_bpr import CollaborativeBPR

    PATH_BARES = "data/jaen/bares_finales.csv"
    PATH_OPINIONES = "data/jaen/opiniones.csv"
    PATH_USUARIOS = "data/jaen/usuarios_finales.csv"

    cb_model = ContentBasedRecommender(
        bars_csv=PATH_BARES,
        opinions_csv=PATH_OPINIONES,
        bar_embeddings_path="data/jaen/embeddings/embeddings_bares.npy",
        bar_index_path="data/jaen/embeddings/embeddings_index.csv",
        user_embeddings_path="data/jaen/embeddings/user_embeddings.npy",
        user_index_path="data/jaen/embeddings/user_embeddings_index.csv"
    )

    bpr_model = CollaborativeBPR(
        k=50,
        max_iter=100,
        learning_rate=0.01,
        lambda_reg=0.01
    )
    bpr_model.fit(PATH_OPINIONES, bars_csv=PATH_BARES)

    hybrid_model = HybridRecommender(
        content_model=cb_model,
        collaborative_model=bpr_model,
        usuarios_csv=PATH_USUARIOS
    )

    test_user = 9800

    resultado = hybrid_model.recommend(test_user, k=10, exclude_seen=True)

    print(f"Usuario {resultado['user_id']}")
    print(f"Número de interacciones: {resultado['n_interacciones']}")
    print(resultado["mensaje"])
    print("Recomendaciones finales:")

    if len(resultado["recomendaciones"]) == 0:
        print("No hay recomendaciones para este usuario")
    else:
        for r in resultado["recomendaciones"]:
            print(r)