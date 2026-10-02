# ============================================================
# Nombre del alumno: Adrián Murillo Moreno
# Descripción: Generar embeddings semánticos de los bares
#              y guardar también el índice placeID -> row_idx
# ============================================================
import pandas as pd
import numpy as np
import re
from sentence_transformers import SentenceTransformer

# =========================
# CONFIGURACIÓN
# =========================

INPUT_BARES_CSV = "data/jaen/bares_finales.csv"
INPUT_OPINIONES_CSV = "data/jaen/opiniones.csv"

OUTPUT_EMB = "data/jaen/embeddings/embeddings_bares.npy"
OUTPUT_INDEX = "data/jaen/embeddings/embeddings_index.csv"

MODEL_NAME = "all-MiniLM-L6-v2"

# Número máximo de reseñas por bar
MAX_REVIEWS_TOTAL = 12
MAX_POS_REVIEWS = 9
MAX_NEG_REVIEWS = 3

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

# Limpia texto para que no meta ruido innecesario
def limpiar_texto(texto):
    if esta_vacio(texto):
        return ""

    texto = str(texto).strip()

    # Reemplazar separadores raros por espacios
    texto = texto.replace("|", " ")
    texto = texto.replace("\n", " ")
    texto = texto.replace("\r", " ")

    # Compactar espacios
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto

# Convierte tipos del estilo "bar|restaurant" a algo más legible
def normalizar_types(types_text):
    if esta_vacio(types_text):
        return ""

    texto = str(types_text).replace("|", ", ")
    texto = limpiar_texto(texto)

    return texto

# Resume de forma simple el horario para no meter demasiado ruido
def resumir_horario(horario):
    if esta_vacio(horario):
        return ""

    texto = str(horario).strip()

    # Separar por días
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

        # Detectar si viernes/sábado/domingo cierran tarde
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

# Puntúa una reseña para elegir las más útiles
def puntuar_resena(texto, rating):
    texto_limpio = limpiar_texto(texto)
    longitud = len(texto_limpio)

    if longitud == 0:
        return -1

    # Penalizar textos demasiado cortos
    if longitud < 20:
        penalizacion_corto = -30
    else:
        penalizacion_corto = 0

    # Penalizar textos excesivamente largos
    if longitud > 900:
        penalizacion_largo = -20
    else:
        penalizacion_largo = 0

    # Bonus por longitud media-informativa
    bonus_longitud = min(longitud / 25, 40)

    # Bonus leve por rating alto, pero sin exagerar
    bonus_rating = float(rating) * 3

    return bonus_longitud + bonus_rating + penalizacion_corto + penalizacion_largo

# Selecciona reseñas útiles de un bar
def seleccionar_resenas(df_bar_reviews):
    if df_bar_reviews.empty:
        return []

    df = df_bar_reviews.copy()

    # Limpiar textos
    df["text"] = df["text"].fillna("").astype(str).apply(limpiar_texto)

    # Quitar reseñas sin texto
    df = df[df["text"] != ""].copy()

    if df.empty:
        return []

    # Asegurar rating numérico
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df.dropna(subset=["rating"]).copy()

    if df.empty:
        return []

    # Quitar textos duplicados exactos dentro del mismo bar
    df = df.drop_duplicates(subset=["text"]).copy()

    # Puntuar reseñas
    df["score_review"] = df.apply(
        lambda fila: puntuar_resena(fila["text"], fila["rating"]),
        axis=1
    )

    # Separar positivas y no positivas
    positivas = df[df["rating"] >= 4.0].copy()
    negativas = df[df["rating"] < 4.0].copy()

    # Ordenar por puntuación
    positivas = positivas.sort_values(by="score_review", ascending=False)
    negativas = negativas.sort_values(by="score_review", ascending=False)

    seleccionadas = []

    # Añadir positivas primero
    for _, fila in positivas.head(MAX_POS_REVIEWS).iterrows():
        seleccionadas.append(f"Opinión positiva: {fila['text']}")

    # Añadir algunas negativas o medias para equilibrar
    for _, fila in negativas.head(MAX_NEG_REVIEWS).iterrows():
        seleccionadas.append(f"Opinión crítica: {fila['text']}")

    # Limitar el total final
    seleccionadas = seleccionadas[:MAX_REVIEWS_TOTAL]

    return seleccionadas

# Construye el texto final del bar
def construir_texto_bar(fila_bar, opiniones_bar):
    bloques = []

    nombre = limpiar_texto(fila_bar.get("nombre", ""))
    types = normalizar_types(fila_bar.get("types", ""))
    descripcion = limpiar_texto(fila_bar.get("descripcion", ""))
    precio = limpiar_texto(fila_bar.get("price_level", ""))
    horario = resumir_horario(fila_bar.get("opening_hours_weekday_text", ""))
    calle = limpiar_texto(fila_bar.get("calle", ""))

    if nombre != "":
        bloques.append(f"Nombre del bar: {nombre}.")

    if types != "":
        bloques.append(f"Tipo de local: {types}.")

    if descripcion != "":
        bloques.append(f"Descripción: {descripcion}.")

    if precio != "":
        bloques.append(f"Rango de precio: {precio}.")

    if calle != "":
        bloques.append(f"Ubicación: {calle}.")

    if horario != "":
        bloques.append(f"Horario resumido: {horario}.")

    if len(opiniones_bar) > 0:
        bloques.append("Opiniones destacadas del local:")
        bloques.extend(opiniones_bar)

    texto_final = " ".join(bloques)
    texto_final = re.sub(r"\s+", " ", texto_final).strip()

    return texto_final

# =========================
# CARGAR DATOS
# =========================

bares = pd.read_csv(INPUT_BARES_CSV)
opiniones = pd.read_csv(INPUT_OPINIONES_CSV)

# =========================
# VALIDACIONES
# =========================

if "placeID" not in bares.columns:
    raise ValueError(f"El CSV de bares debe contener 'placeID'. Columnas actuales: {list(bares.columns)}")

if "placeID" not in opiniones.columns or "text" not in opiniones.columns or "rating" not in opiniones.columns:
    raise ValueError(
        "El CSV de opiniones debe contener las columnas 'placeID', 'text' y 'rating'."
    )

# Normalizar IDs
bares["placeID"] = pd.to_numeric(bares["placeID"], errors="coerce")
opiniones["placeID"] = pd.to_numeric(opiniones["placeID"], errors="coerce")

if bares["placeID"].isna().any():
    raise ValueError("Hay valores vacíos o no numéricos en 'placeID' de bares.")

bares["placeID"] = bares["placeID"].astype(int)
opiniones = opiniones.dropna(subset=["placeID"]).copy()
opiniones["placeID"] = opiniones["placeID"].astype(int)

# =========================
# AGRUPAR OPINIONES POR BAR
# =========================

opiniones_por_bar = {
    place_id: grupo.copy()
    for place_id, grupo in opiniones.groupby("placeID")
}

# =========================
# CONSTRUIR TEXTO SEMÁNTICO NUEVO
# =========================

textos = []

print("Construyendo textos semánticos de bares...")

for _, fila_bar in bares.iterrows():
    place_id = int(fila_bar["placeID"])

    df_bar_reviews = opiniones_por_bar.get(place_id, pd.DataFrame(columns=opiniones.columns))
    reseñas_seleccionadas = seleccionar_resenas(df_bar_reviews)

    texto_bar = construir_texto_bar(fila_bar, reseñas_seleccionadas)
    textos.append(texto_bar)

# =========================
# CARGAR MODELO
# =========================

model = SentenceTransformer(MODEL_NAME)

# =========================
# GENERAR EMBEDDINGS
# =========================

print("Generando embeddings de bares...")

embeddings = model.encode(
    textos,
    show_progress_bar=True
)

# =========================
# GUARDAR EMBEDDINGS
# =========================

np.save(OUTPUT_EMB, embeddings)

# =========================
# GUARDAR ÍNDICE
# =========================

df_index = pd.DataFrame({
    "placeID": bares["placeID"].tolist(),
    "row_idx": range(len(bares))
})

df_index.to_csv(OUTPUT_INDEX, index=False)


# =========================
# COMPROBACIÓN FINAL
# =========================

print("Embeddings generados:", embeddings.shape)
print("Archivo generado:", OUTPUT_EMB)
print("Archivo generado:", OUTPUT_INDEX)
print("Archivo generado: data/jaen/embeddings/textos_bares_generados.csv")
print("Filas índice:", len(df_index))