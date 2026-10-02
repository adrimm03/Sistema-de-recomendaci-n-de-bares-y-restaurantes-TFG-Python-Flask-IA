import threading
import time
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from src.models.content_based import ContentBasedRecommender
from src.models.collaborative_bpr import CollaborativeBPR
from src.models.hybrid_switching import HybridRecommender


MODEL_NAME = "all-MiniLM-L6-v2"

USERS_CSV = Path("data/jaen/usuarios_finales.csv")
BARES_CSV = Path("data/jaen/bares_finales.csv")
OPINIONES_CSV = Path("data/jaen/opiniones.csv")

BAR_EMB_PATH = Path("data/jaen/embeddings/embeddings_bares.npy")
BAR_INDEX_PATH = Path("data/jaen/embeddings/embeddings_index.csv")
USER_EMB_PATH = Path("data/jaen/embeddings/user_embeddings.npy")
USER_INDEX_PATH = Path("data/jaen/embeddings/user_embeddings_index.csv")

_LOCK = threading.Lock()
_BPR_DIRTY = False
_BPR_LAST_DIRTY_TS = 0.0


def esta_vacio(valor):
    if pd.isna(valor):
        return True
    return str(valor).strip() == ""


def limpiar_texto(texto):
    if esta_vacio(texto):
        return ""
    texto = str(texto).strip()
    texto = texto.replace("|", " ")
    texto = texto.replace("\n", " ")
    texto = texto.replace("\r", " ")
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def normalizar_types(types_text):
    if esta_vacio(types_text):
        return ""
    return limpiar_texto(str(types_text).replace("|", ", "))


def resumir_horario(horario):
    if esta_vacio(horario):
        return ""

    texto = str(horario).strip()
    partes = [p.strip() for p in texto.split("|") if p.strip() != ""]

    if len(partes) == 0:
        return ""

    dias_abiertos = 0
    dias_cerrados = 0
    abre_finde_tarde = False

    for parte in partes:
        parte_lower = parte.lower()

        if "cerrado" in parte_lower:
            dias_cerrados += 1
        else:
            dias_abiertos += 1

        if (
            ("viernes" in parte_lower or "sábado" in parte_lower or "sabado" in parte_lower or "domingo" in parte_lower)
            and ("24:00" in parte_lower or "23:" in parte_lower or "00:" in parte_lower)
        ):
            abre_finde_tarde = True

    resumen = []
    if dias_abiertos > 0:
        resumen.append(f"Abre {dias_abiertos} días a la semana")
    if dias_cerrados > 0:
        resumen.append(f"Cierra {dias_cerrados} días a la semana")
    if abre_finde_tarde:
        resumen.append("Abre hasta tarde en fin de semana")

    return ". ".join(resumen)


def construir_contexto_bar(fila_bar):
    bloques = []

    nombre = limpiar_texto(fila_bar.get("nombre", ""))
    types = normalizar_types(fila_bar.get("types", ""))
    descripcion = limpiar_texto(fila_bar.get("descripcion", ""))
    precio = limpiar_texto(fila_bar.get("price_level", ""))
    horario = resumir_horario(fila_bar.get("opening_hours_weekday_text", ""))
    calle = limpiar_texto(fila_bar.get("calle", ""))

    if nombre:
        bloques.append(f"Bar: {nombre}.")
    if types:
        bloques.append(f"Tipo: {types}.")
    if descripcion:
        bloques.append(f"Descripción: {descripcion}.")
    if precio:
        bloques.append(f"Precio: {precio}.")
    if calle:
        bloques.append(f"Ubicación: {calle}.")
    if horario:
        bloques.append(f"Horario: {horario}.")

    return " ".join(bloques).strip()


def puntuar_resena(texto, rating):
    texto_limpio = limpiar_texto(texto)
    longitud = len(texto_limpio)

    if longitud == 0:
        return -1

    penalizacion_corto = -30 if longitud < 20 else 0
    penalizacion_largo = -20 if longitud > 900 else 0
    bonus_longitud = min(longitud / 25, 40)
    bonus_rating = float(rating) * 3

    return bonus_longitud + bonus_rating + penalizacion_corto + penalizacion_largo


def seleccionar_resenas(df_bar_reviews, max_total=12, max_pos=9, max_neg=3):
    if df_bar_reviews.empty:
        return []

    df = df_bar_reviews.copy()
    df["text"] = df["text"].fillna("").astype(str).apply(limpiar_texto)
    df = df[df["text"] != ""].copy()

    if df.empty:
        return []

    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df.dropna(subset=["rating"]).copy()
    df = df.drop_duplicates(subset=["text"]).copy()

    if df.empty:
        return []

    df["score_review"] = df.apply(
        lambda fila: puntuar_resena(fila["text"], fila["rating"]),
        axis=1
    )

    positivas = df[df["rating"] >= 4.0].sort_values(by="score_review", ascending=False)
    negativas = df[df["rating"] < 4.0].sort_values(by="score_review", ascending=False)

    seleccionadas = []

    for _, fila in positivas.head(max_pos).iterrows():
        seleccionadas.append(f"Opinión positiva: {fila['text']}")

    for _, fila in negativas.head(max_neg).iterrows():
        seleccionadas.append(f"Opinión crítica: {fila['text']}")

    return seleccionadas[:max_total]


def construir_texto_bar(fila_bar, opiniones_bar):
    bloques = []

    nombre = limpiar_texto(fila_bar.get("nombre", ""))
    types = normalizar_types(fila_bar.get("types", ""))
    descripcion = limpiar_texto(fila_bar.get("descripcion", ""))
    precio = limpiar_texto(fila_bar.get("price_level", ""))
    horario = resumir_horario(fila_bar.get("opening_hours_weekday_text", ""))
    calle = limpiar_texto(fila_bar.get("calle", ""))

    if nombre:
        bloques.append(f"Nombre del bar: {nombre}.")
    if types:
        bloques.append(f"Tipo de local: {types}.")
    if descripcion:
        bloques.append(f"Descripción: {descripcion}.")
    if precio:
        bloques.append(f"Rango de precio: {precio}.")
    if calle:
        bloques.append(f"Ubicación: {calle}.")
    if horario:
        bloques.append(f"Horario resumido: {horario}.")

    if opiniones_bar:
        bloques.append("Opiniones destacadas del local:")
        bloques.extend(opiniones_bar)

    return re.sub(r"\s+", " ", " ".join(bloques)).strip()


def puntuar_fragmento(texto, rating):
    texto_limpio = limpiar_texto(texto)
    longitud = len(texto_limpio)

    if longitud == 0:
        return -1

    penalizacion_corto = -25 if longitud < 20 else 0
    penalizacion_largo = -15 if longitud > 1200 else 0
    bonus_longitud = min(longitud / 25, 45)
    bonus_rating = float(rating) * 4

    return bonus_longitud + bonus_rating + penalizacion_corto + penalizacion_largo


def media_ponderada_embeddings(grupo):
    matriz = np.vstack(grupo["embedding"].values)
    pesos = grupo["peso"].astype(float).values

    if np.sum(pesos) == 0:
        return np.mean(matriz, axis=0)

    return np.average(matriz, axis=0, weights=pesos)


def actualizar_metricas_usuario(user_id):
    usuarios = pd.read_csv(USERS_CSV)
    opiniones = pd.read_csv(OPINIONES_CSV)
    bares = pd.read_csv(BARES_CSV)

    usuarios["user_id"] = pd.to_numeric(usuarios["user_id"], errors="coerce")
    opiniones["user_id"] = pd.to_numeric(opiniones["user_id"], errors="coerce")
    opiniones["placeID"] = pd.to_numeric(opiniones["placeID"], errors="coerce")
    opiniones["rating"] = pd.to_numeric(opiniones["rating"], errors="coerce")
    bares["placeID"] = pd.to_numeric(bares["placeID"], errors="coerce")

    # Forzar columnas de texto para evitar errores de dtype
    if "top_types" in usuarios.columns:
        usuarios["top_types"] = usuarios["top_types"].fillna("").astype(str)

    if "avg_price_level_likes" in usuarios.columns:
        usuarios["avg_price_level_likes"] = usuarios["avg_price_level_likes"].fillna("").astype(str)

    opiniones_u = opiniones[opiniones["user_id"] == user_id].copy()
    n_interacciones = len(opiniones_u)

    top_types = ""
    avg_price = ""

    if not opiniones_u.empty:
        opiniones_u = opiniones_u.merge(
            bares[["placeID", "types", "price_level"]],
            on="placeID",
            how="left"
        )

        tipos = []
        for valor in opiniones_u["types"].fillna("").astype(str):
            tipos.extend([t.strip() for t in valor.split("|") if t.strip()])

        if tipos:
            top_types = ", ".join(pd.Series(tipos).value_counts().head(3).index.tolist())

        def price_to_num(x):
            x = str(x).strip()
            if x == "1-10€":
                return 1
            if x == "10-20€":
                return 2
            if x == "20-30€":
                return 3
            return np.nan

        nums = opiniones_u["price_level"].apply(price_to_num).dropna()
        if not nums.empty:
            media = nums.mean()
            if media < 1.5:
                avg_price = "€"
            elif media < 2.5:
                avg_price = "€€"
            else:
                avg_price = "€€€"

    idx = usuarios["user_id"] == user_id
    usuarios.loc[idx, "n_interacciones"] = int(n_interacciones)
    usuarios.loc[idx, "top_types"] = str(top_types)
    usuarios.loc[idx, "avg_price_level_likes"] = str(avg_price)

    usuarios.to_csv(USERS_CSV, index=False, encoding="utf-8")


def actualizar_metricas_bar(place_id):
    bares = pd.read_csv(BARES_CSV)
    opiniones = pd.read_csv(OPINIONES_CSV)

    bares["placeID"] = pd.to_numeric(bares["placeID"], errors="coerce")
    opiniones["placeID"] = pd.to_numeric(opiniones["placeID"], errors="coerce")
    opiniones["rating"] = pd.to_numeric(opiniones["rating"], errors="coerce")

    op_bar = opiniones[(opiniones["placeID"] == place_id) & opiniones["rating"].notna()].copy()

    idx = bares["placeID"] == place_id
    if op_bar.empty:
        bares.loc[idx, "val_media"] = ""
        bares.loc[idx, "num_val"] = 0
    else:
        bares.loc[idx, "val_media"] = round(op_bar["rating"].mean(), 2)
        bares.loc[idx, "num_val"] = int(op_bar["rating"].count())

    bares.to_csv(BARES_CSV, index=False, encoding="utf-8")


def actualizar_embedding_bar(place_id):
    model = SentenceTransformer(MODEL_NAME)
    bares = pd.read_csv(BARES_CSV)
    opiniones = pd.read_csv(OPINIONES_CSV)
    emb = np.load(BAR_EMB_PATH)
    idx_df = pd.read_csv(BAR_INDEX_PATH)

    bares["placeID"] = pd.to_numeric(bares["placeID"], errors="coerce")
    opiniones["placeID"] = pd.to_numeric(opiniones["placeID"], errors="coerce")
    idx_df["placeID"] = pd.to_numeric(idx_df["placeID"], errors="coerce")
    idx_df["row_idx"] = pd.to_numeric(idx_df["row_idx"], errors="coerce")

    fila_bar = bares[bares["placeID"] == place_id]
    if fila_bar.empty:
        return

    fila_bar = fila_bar.iloc[0]
    op_bar = opiniones[opiniones["placeID"] == place_id].copy()
    opiniones_sel = seleccionar_resenas(op_bar)
    texto = construir_texto_bar(fila_bar, opiniones_sel)

    nuevo_vec = model.encode([texto], show_progress_bar=False)[0]

    fila_idx = idx_df[idx_df["placeID"] == place_id]
    if fila_idx.empty:
        nuevo_row = len(emb)
        emb = np.vstack([emb, nuevo_vec])
        idx_df = pd.concat(
            [idx_df, pd.DataFrame([{"placeID": int(place_id), "row_idx": nuevo_row}])],
            ignore_index=True
        )
    else:
        row = int(fila_idx.iloc[0]["row_idx"])
        emb[row] = nuevo_vec

    np.save(BAR_EMB_PATH, emb)
    idx_df.to_csv(BAR_INDEX_PATH, index=False)


def actualizar_embedding_usuario(user_id):
    model = SentenceTransformer(MODEL_NAME)
    opiniones = pd.read_csv(OPINIONES_CSV)
    bares = pd.read_csv(BARES_CSV)
    emb = np.load(USER_EMB_PATH)
    idx_df = pd.read_csv(USER_INDEX_PATH)

    opiniones["placeID"] = pd.to_numeric(opiniones["placeID"], errors="coerce")
    opiniones["user_id"] = pd.to_numeric(opiniones["user_id"], errors="coerce")
    opiniones["rating"] = pd.to_numeric(opiniones["rating"], errors="coerce")
    bares["placeID"] = pd.to_numeric(bares["placeID"], errors="coerce")
    idx_df["user_id"] = pd.to_numeric(idx_df["user_id"], errors="coerce")
    idx_df["row_idx"] = pd.to_numeric(idx_df["row_idx"], errors="coerce")

    opiniones_u = opiniones[
        (opiniones["user_id"] == user_id) &
        (opiniones["rating"] >= 4.0)
    ].copy()

    if opiniones_u.empty:
        return

    bares["contexto_bar"] = bares.apply(construir_contexto_bar, axis=1)
    mapa_contexto = dict(zip(bares["placeID"], bares["contexto_bar"]))

    registros = []

    for _, fila in opiniones_u.iterrows():
        place_id = int(fila["placeID"])
        rating = float(fila["rating"])
        texto_op = limpiar_texto(fila.get("text", ""))
        contexto = mapa_contexto.get(place_id, "")

        if texto_op:
            frag = f"Opinión positiva del usuario sobre un bar que le gustó. Valoración: {rating}. Comentario: {texto_op}"
            score = puntuar_fragmento(frag, rating)
            registros.append({"fragmento": frag, "peso": max(score, 1.0)})

        if contexto:
            frag = f"Bar valorado positivamente por el usuario. Valoración: {rating}. {contexto}"
            score = puntuar_fragmento(frag, rating)
            registros.append({"fragmento": frag, "peso": max(score * 0.8, 1.0)})

    if not registros:
        return

    df_frag = pd.DataFrame(registros).sort_values(by="peso", ascending=False).head(15)
    vecs = model.encode(df_frag["fragmento"].tolist(), show_progress_bar=False)
    df_frag["embedding"] = list(vecs)
    user_vec = media_ponderada_embeddings(df_frag)

    fila_idx = idx_df[idx_df["user_id"] == user_id]
    if fila_idx.empty:
        nuevo_row = len(emb)
        emb = np.vstack([emb, user_vec])
        idx_df = pd.concat(
            [idx_df, pd.DataFrame([{"user_id": int(user_id), "row_idx": nuevo_row}])],
            ignore_index=True
        )
    else:
        row = int(fila_idx.iloc[0]["row_idx"])
        emb[row] = user_vec

    np.save(USER_EMB_PATH, emb)
    idx_df.to_csv(USER_INDEX_PATH, index=False)


def refrescar_content_y_hibrido(app_module):
    app_module.cb_model = ContentBasedRecommender(
        bars_csv="data/jaen/bares_finales.csv",
        opinions_csv="data/jaen/opiniones.csv",
        bar_embeddings_path="data/jaen/embeddings/embeddings_bares.npy",
        bar_index_path="data/jaen/embeddings/embeddings_index.csv",
        user_embeddings_path="data/jaen/embeddings/user_embeddings.npy",
        user_index_path="data/jaen/embeddings/user_embeddings_index.csv"
    )

    app_module.hybrid_model = HybridRecommender(
        content_model=app_module.cb_model,
        collaborative_model=app_module.bpr_model,
        usuarios_csv="data/jaen/usuarios_finales.csv"
    )


def refrescar_recomendacion_local(app_module, user_id, place_id):
    with _LOCK:
        actualizar_metricas_usuario(user_id)
        actualizar_metricas_bar(place_id)
        actualizar_embedding_usuario(user_id)
        actualizar_embedding_bar(place_id)
        refrescar_content_y_hibrido(app_module)

    marcar_bpr_como_sucio()


def marcar_bpr_como_sucio():
    global _BPR_DIRTY, _BPR_LAST_DIRTY_TS
    _BPR_DIRTY = True
    _BPR_LAST_DIRTY_TS = time.time()


def worker_bpr(app_module, cooldown_seconds=15):
    global _BPR_DIRTY, _BPR_LAST_DIRTY_TS

    while True:
        time.sleep(3)

        if not _BPR_DIRTY:
            continue

        if time.time() - _BPR_LAST_DIRTY_TS < cooldown_seconds:
            continue

        try:
            with _LOCK:
                nuevo_bpr = CollaborativeBPR(
                    k=50,
                    max_iter=100,
                    learning_rate=0.01,
                    lambda_reg=0.01
                )
                nuevo_bpr.fit(
                    "data/jaen/opiniones.csv",
                    bars_csv="data/jaen/bares_finales.csv"
                )

                app_module.bpr_model = nuevo_bpr
                app_module.hybrid_model = HybridRecommender(
                    content_model=app_module.cb_model,
                    collaborative_model=app_module.bpr_model,
                    usuarios_csv="data/jaen/usuarios_finales.csv"
                )

                _BPR_DIRTY = False
        except Exception as e:
            print(f"[BPR] Error reentrenando modelo: {e}")


def lanzar_worker_bpr(app_module):
    hilo = threading.Thread(target=worker_bpr, args=(app_module,), daemon=True)
    hilo.start()