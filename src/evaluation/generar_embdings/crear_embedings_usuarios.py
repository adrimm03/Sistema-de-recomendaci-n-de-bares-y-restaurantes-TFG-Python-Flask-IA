# Nombre del alumno: Adrián Murillo Moreno
# Descripción breve del ejercicio:
# Genera embeddings de usuarios a partir de sus opiniones positivas
# y del contexto semántico de los bares que les han gustado.
# Guarda también el índice user_id -> row_idx.

import pandas as pd
import numpy as np
import re
from sentence_transformers import SentenceTransformer

# =========================
# CONFIGURACIÓN
# =========================

INPUT_OPINIONES_CSV = "data/jaen/opiniones.csv"
INPUT_BARES_CSV = "data/jaen/bares_finales.csv"

OUTPUT_EMB = "data/jaen/embeddings/user_embeddings.npy"
OUTPUT_INDEX = "data/jaen/embeddings/user_embeddings_index.csv"
OUTPUT_TEXTS = "data/jaen/embeddings/textos_usuarios_generados.csv"

MODEL_NAME = "all-MiniLM-L6-v2"

# Solo consideramos opiniones positivas para modelar gustos
MIN_RATING_POSITIVE = 4.0

# Máximo de fragmentos por usuario para evitar ruido excesivo
MAX_TEXTS_PER_USER = 15

# =========================
# FUNCIONES AUXILIARES
# =========================

# Comprueba si un valor está vacío
def esta_vacio(valor):
    if pd.isna(valor):
        return True
    if str(valor).strip() == "":
        return True
    return False

# Limpia texto para reducir ruido
def limpiar_texto(texto):
    if esta_vacio(texto):
        return ""

    texto = str(texto).strip()
    texto = texto.replace("|", " ")
    texto = texto.replace("\n", " ")
    texto = texto.replace("\r", " ")
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto

# Convierte los tipos a formato legible
def normalizar_types(types_text):
    if esta_vacio(types_text):
        return ""

    texto = str(types_text).replace("|", ", ")
    texto = limpiar_texto(texto)

    return texto

# Resume el horario para no meter texto bruto excesivo
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

# Construye una descripción compacta del bar
def construir_contexto_bar(fila_bar):
    bloques = []

    nombre = limpiar_texto(fila_bar.get("nombre", ""))
    types = normalizar_types(fila_bar.get("types", ""))
    descripcion = limpiar_texto(fila_bar.get("descripcion", ""))
    precio = limpiar_texto(fila_bar.get("price_level", ""))
    horario = resumir_horario(fila_bar.get("opening_hours_weekday_text", ""))
    calle = limpiar_texto(fila_bar.get("calle", ""))

    if nombre != "":
        bloques.append(f"Bar: {nombre}.")
    if types != "":
        bloques.append(f"Tipo: {types}.")
    if descripcion != "":
        bloques.append(f"Descripción: {descripcion}.")
    if precio != "":
        bloques.append(f"Precio: {precio}.")
    if calle != "":
        bloques.append(f"Ubicación: {calle}.")
    if horario != "":
        bloques.append(f"Horario: {horario}.")

    return " ".join(bloques).strip()

# Puntúa un fragmento textual para quedarnos con los más útiles
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

# =========================
# CARGAR DATOS
# =========================

opiniones = pd.read_csv(INPUT_OPINIONES_CSV)
bares = pd.read_csv(INPUT_BARES_CSV)

# =========================
# VALIDACIONES
# =========================

columnas_opiniones = {"placeID", "user_id", "rating", "text"}
columnas_bares = {"placeID", "nombre", "types", "descripcion", "price_level", "opening_hours_weekday_text", "calle"}

if not columnas_opiniones.issubset(opiniones.columns):
    raise ValueError(
        f"El CSV de opiniones debe contener las columnas {columnas_opiniones}. "
        f"Columnas actuales: {list(opiniones.columns)}"
    )

if not {"placeID"}.issubset(bares.columns):
    raise ValueError(
        f"El CSV de bares debe contener al menos 'placeID'. "
        f"Columnas actuales: {list(bares.columns)}"
    )

# =========================
# NORMALIZAR TIPOS
# =========================

opiniones["placeID"] = pd.to_numeric(opiniones["placeID"], errors="coerce")
opiniones["user_id"] = pd.to_numeric(opiniones["user_id"], errors="coerce")
opiniones["rating"] = pd.to_numeric(opiniones["rating"], errors="coerce")

bares["placeID"] = pd.to_numeric(bares["placeID"], errors="coerce")

opiniones = opiniones.dropna(subset=["placeID", "user_id", "rating"]).copy()
bares = bares.dropna(subset=["placeID"]).copy()

opiniones["placeID"] = opiniones["placeID"].astype(int)
opiniones["user_id"] = opiniones["user_id"].astype(int)
bares["placeID"] = bares["placeID"].astype(int)

# =========================
# FILTRAR OPINIONES POSITIVAS
# =========================

opiniones = opiniones[opiniones["rating"] >= MIN_RATING_POSITIVE].copy()
opiniones["text"] = opiniones["text"].fillna("").astype(str).apply(limpiar_texto)

# =========================
# MAPA DE CONTEXTO DE BARES
# =========================

bares_contexto = bares.copy()
bares_contexto["contexto_bar"] = bares_contexto.apply(construir_contexto_bar, axis=1)

mapa_contexto_bar = dict(zip(bares_contexto["placeID"], bares_contexto["contexto_bar"]))

# =========================
# CONSTRUIR TEXTOS POR USUARIO
# =========================

registros_fragmentos = []

for _, fila in opiniones.iterrows():
    user_id = int(fila["user_id"])
    place_id = int(fila["placeID"])
    rating = float(fila["rating"])
    texto_opinion = limpiar_texto(fila["text"])
    contexto_bar = mapa_contexto_bar.get(place_id, "")

    # Fragmento 1: lo que escribió el usuario
    if texto_opinion != "":
        fragmento_opinion = (
            f"Opinión positiva del usuario sobre un bar que le gustó. "
            f"Valoración: {rating}. Comentario: {texto_opinion}"
        )
        score_fragmento = puntuar_fragmento(fragmento_opinion, rating)

        registros_fragmentos.append({
            "user_id": user_id,
            "placeID": place_id,
            "rating": rating,
            "fragmento": fragmento_opinion,
            "peso": max(score_fragmento, 1.0)
        })

    # Fragmento 2: contexto del bar que le gustó
    if contexto_bar != "":
        fragmento_bar = (
            f"Bar valorado positivamente por el usuario. "
            f"Valoración: {rating}. {contexto_bar}"
        )
        score_fragmento = puntuar_fragmento(fragmento_bar, rating)

        registros_fragmentos.append({
            "user_id": user_id,
            "placeID": place_id,
            "rating": rating,
            "fragmento": fragmento_bar,
            "peso": max(score_fragmento * 0.8, 1.0)
        })

# Convertir a DataFrame
df_fragmentos = pd.DataFrame(registros_fragmentos)

if df_fragmentos.empty:
    raise ValueError("No se han podido construir fragmentos válidos para generar embeddings de usuarios.")

# =========================
# LIMITAR FRAGMENTOS POR USUARIO
# =========================

df_fragmentos = df_fragmentos.sort_values(
    by=["user_id", "peso"],
    ascending=[True, False]
).copy()

df_fragmentos["rank_usuario"] = df_fragmentos.groupby("user_id").cumcount() + 1
df_fragmentos = df_fragmentos[df_fragmentos["rank_usuario"] <= MAX_TEXTS_PER_USER].copy()

# =========================
# GENERAR EMBEDDINGS DE FRAGMENTOS
# =========================

model = SentenceTransformer(MODEL_NAME)

print("Generando embeddings de fragmentos de usuario...")

embeddings_fragmentos = model.encode(
    df_fragmentos["fragmento"].tolist(),
    show_progress_bar=True
)

df_fragmentos["embedding"] = list(embeddings_fragmentos)

# =========================
# AGREGAR A NIVEL DE USUARIO
# =========================

def media_ponderada_embeddings(grupo):
    matriz = np.vstack(grupo["embedding"].values)
    pesos = grupo["peso"].astype(float).values

    if np.sum(pesos) == 0:
        return np.mean(matriz, axis=0)

    return np.average(matriz, axis=0, weights=pesos)

user_embeddings_series = (
    df_fragmentos.groupby("user_id")
    .apply(media_ponderada_embeddings)
)

user_ids = user_embeddings_series.index.tolist()
user_matrix = np.vstack(user_embeddings_series.values)

# =========================
# GUARDAR EMBEDDINGS
# =========================

np.save(OUTPUT_EMB, user_matrix)

# =========================
# GUARDAR ÍNDICE
# =========================

df_index = pd.DataFrame({
    "user_id": user_ids,
    "row_idx": range(len(user_ids))
})

df_index.to_csv(OUTPUT_INDEX, index=False)


# =========================
# COMPROBACIÓN FINAL
# =========================

print("Usuarios con embedding:", len(user_ids))
print("Shape embeddings:", user_matrix.shape)
print("Archivo generado:", OUTPUT_EMB)
print("Archivo generado:", OUTPUT_INDEX)