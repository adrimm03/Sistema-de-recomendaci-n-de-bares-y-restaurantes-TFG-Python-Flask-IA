# Adrián Murillo Moreno
# Script para enriquecer los datos normalizados del sistema
# Lee bares, usuarios, opiniones, favoritos y códigos postales
# y genera dos JSON enriquecidos listos para usar en la aplicación.

import json
from pathlib import Path
import pandas as pd


def normalizar_cod_postal(valor):
    """Convierte el código postal a string limpio sin .0."""
    if pd.isna(valor) or str(valor).strip() == "":
        return ""

    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]

    return texto


def dividir_campo_pipe(valor):
    """Convierte un texto separado por | en una lista."""
    if pd.isna(valor) or str(valor).strip() == "":
        return []

    return [parte.strip() for parte in str(valor).split("|") if parte.strip() != ""]


def valor_seguro_texto(valor):
    """Devuelve string limpio o cadena vacía."""
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def cargar_csv(ruta_csv):
    """Carga un CSV y devuelve un DataFrame."""
    return pd.read_csv(ruta_csv)


def construir_mapa_cp(df_cp):
    """
    Construye un diccionario:
    {
        "23001": {"ciudad": "...", "provincia": "...", "pais": "..."}
    }
    """
    mapa_cp = {}

    for _, fila in df_cp.iterrows():
        postal_code = normalizar_cod_postal(fila.get("postal_code", ""))

        if postal_code == "":
            continue

        mapa_cp[postal_code] = {
            "ciudad": valor_seguro_texto(fila.get("ciudad", "")),
            "provincia": valor_seguro_texto(fila.get("provincia", "")),
            "pais": valor_seguro_texto(fila.get("pais", "")),
        }

    return mapa_cp


def construir_mapa_usernames(df_usuarios):
    """Devuelve un diccionario user_id -> username."""
    mapa_usernames = {}

    for _, fila_usuario in df_usuarios.iterrows():
        user_id = int(pd.to_numeric(fila_usuario.get("user_id", 0), errors="coerce"))
        username = valor_seguro_texto(fila_usuario.get("username", ""))
        mapa_usernames[user_id] = username

    return mapa_usernames


def construir_opiniones_por_bar(df_opiniones, mapa_usernames):
    """Agrupa opiniones por placeID."""
    opiniones_por_bar = {}

    for _, fila in df_opiniones.iterrows():
        place_id = int(pd.to_numeric(fila.get("placeID", 0), errors="coerce"))
        user_id = int(pd.to_numeric(fila.get("user_id", 0), errors="coerce"))
        rating = int(pd.to_numeric(fila.get("rating", 0), errors="coerce"))

        opinion = {
            "placeID": place_id,
            "user_id": user_id,
            "username": mapa_usernames.get(user_id, ""),
            "rating": rating,
            "text": valor_seguro_texto(fila.get("text", "")),
            "fecha_publicacion": valor_seguro_texto(fila.get("fecha_publicacion", "")),
        }

        if place_id not in opiniones_por_bar:
            opiniones_por_bar[place_id] = []

        opiniones_por_bar[place_id].append(opinion)

    return opiniones_por_bar


def construir_opiniones_por_usuario(df_opiniones):
    """Agrupa opiniones por user_id."""
    opiniones_por_usuario = {}

    for _, fila in df_opiniones.iterrows():
        place_id = int(pd.to_numeric(fila.get("placeID", 0), errors="coerce"))
        user_id = int(pd.to_numeric(fila.get("user_id", 0), errors="coerce"))
        rating = int(pd.to_numeric(fila.get("rating", 0), errors="coerce"))

        opinion = {
            "placeID": place_id,
            "user_id": user_id,
            "rating": rating,
            "text": valor_seguro_texto(fila.get("text", "")),
            "fecha_publicacion": valor_seguro_texto(fila.get("fecha_publicacion", "")),
        }

        if user_id not in opiniones_por_usuario:
            opiniones_por_usuario[user_id] = []

        opiniones_por_usuario[user_id].append(opinion)

    return opiniones_por_usuario


def construir_favoritos_por_usuario(df_favoritos):
    """Agrupa favoritos por user_id."""
    favoritos_por_usuario = {}

    for _, fila in df_favoritos.iterrows():
        user_id = int(pd.to_numeric(fila.get("user_id", 0), errors="coerce"))
        place_id = int(pd.to_numeric(fila.get("placeID", 0), errors="coerce"))

        if user_id not in favoritos_por_usuario:
            favoritos_por_usuario[user_id] = []

        favoritos_por_usuario[user_id].append(place_id)

    return favoritos_por_usuario


def construir_favoritos_por_bar(df_favoritos):
    """Agrupa favoritos por placeID."""
    favoritos_por_bar = {}

    for _, fila in df_favoritos.iterrows():
        user_id = int(pd.to_numeric(fila.get("user_id", 0), errors="coerce"))
        place_id = int(pd.to_numeric(fila.get("placeID", 0), errors="coerce"))

        if place_id not in favoritos_por_bar:
            favoritos_por_bar[place_id] = []

        favoritos_por_bar[place_id].append(user_id)

    return favoritos_por_bar


def valor_seguro_float(valor, default=0.0):
    numero = pd.to_numeric(valor, errors="coerce")
    if pd.isna(numero):
        return default
    return float(numero)


def valor_seguro_int(valor, default=0):
    numero = pd.to_numeric(valor, errors="coerce")
    if pd.isna(numero):
        return default
    return int(numero)


def enriquecer_bares(df_bares, mapa_cp, opiniones_por_bar, favoritos_por_bar):
    """Genera una lista de bares enriquecidos."""
    bares_enriquecidos = []

    for _, fila in df_bares.iterrows():
        place_id = int(pd.to_numeric(fila.get("placeID", 0), errors="coerce"))
        cod_postal = normalizar_cod_postal(fila.get("cod_postal", ""))

        datos_cp = mapa_cp.get(
            cod_postal,
            {"ciudad": "", "provincia": "", "pais": ""}
        )

        bar = {
            "placeID": place_id,
            "nombre": valor_seguro_texto(fila.get("nombre", "")),
            "lat": float(pd.to_numeric(fila.get("lat", 0.0), errors="coerce")),
            "lon": float(pd.to_numeric(fila.get("lon", 0.0), errors="coerce")),
            "cod_postal": cod_postal,
            "calle": valor_seguro_texto(fila.get("calle", "")),
            "ciudad": datos_cp["ciudad"],
            "provincia": datos_cp["provincia"],
            "pais": datos_cp["pais"],
            "val_media": valor_seguro_float(fila.get("val_media", 0.0), 0.0),
            "num_val": valor_seguro_int(fila.get("num_val", 0), 0),
            "price_level": valor_seguro_texto(fila.get("price_level", "")),
            "website": valor_seguro_texto(fila.get("website", "")),
            "opening_hours_weekday_text": dividir_campo_pipe(fila.get("opening_hours_weekday_text", "")),
            "types": dividir_campo_pipe(fila.get("types", "")),
            "texto_semantico": valor_seguro_texto(fila.get("texto_semantico", "")),
            "photo": valor_seguro_texto(fila.get("photo", "")),
            "descripcion": valor_seguro_texto(fila.get("descripcion", "")),
            "opiniones": opiniones_por_bar.get(place_id, []),
            "favorito_por_usuarios": favoritos_por_bar.get(place_id, [])
        }

        bares_enriquecidos.append(bar)

    return bares_enriquecidos


def enriquecer_usuarios(df_usuarios, mapa_cp, opiniones_por_usuario, favoritos_por_usuario):
    """Genera una lista de usuarios enriquecidos."""
    usuarios_enriquecidos = []

    for _, fila in df_usuarios.iterrows():
        user_id = int(pd.to_numeric(fila.get("user_id", 0), errors="coerce"))
        cod_postal = normalizar_cod_postal(fila.get("cod_postal", ""))

        datos_cp = mapa_cp.get(
            cod_postal,
            {"ciudad": "", "provincia": "", "pais": ""}
        )

        usuario = {
            "user_id": user_id,
            "username": valor_seguro_texto(fila.get("username", "")),
            "preferencias": valor_seguro_texto(fila.get("preferencias", "")),
            "cod_postal": cod_postal,
            "ciudad": datos_cp["ciudad"],
            "provincia": datos_cp["provincia"],
            "pais": datos_cp["pais"],
            "n_interacciones": float(pd.to_numeric(fila.get("n_interacciones", 0), errors="coerce")),
            "top_types": dividir_campo_pipe(fila.get("top_types", "")),
            "avg_price_level_likes": float(pd.to_numeric(fila.get("avg_price_level_likes", 0.0), errors="coerce")),
            "password": valor_seguro_texto(fila.get("password", "")),
            "fecha_nacimiento": valor_seguro_texto(fila.get("fecha_nacimiento", "")),
            "opiniones": opiniones_por_usuario.get(user_id, []),
            "favoritos": favoritos_por_usuario.get(user_id, [])
        }

        usuarios_enriquecidos.append(usuario)

    return usuarios_enriquecidos


def guardar_json(datos, ruta_salida):
    """Guarda una lista o diccionario en JSON UTF-8."""
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    print(f"Archivo generado: {ruta_salida}")


def main():
    # Rutas de entrada
    ruta_bares = Path("data/jaen/bares_finales.csv")
    ruta_usuarios = Path("data/jaen/usuarios_finales.csv")
    ruta_opiniones = Path("data/jaen/opiniones.csv")
    ruta_cp = Path("data/jaen/cp_jaen.csv")
    ruta_favoritos = Path("data/jaen/favoritos.csv")

    # Rutas de salida
    ruta_bares_json = Path("data/jaen/json/bares_enriquecidos.json")
    ruta_usuarios_json = Path("data/jaen/json/usuarios_enriquecidos.json")

    # Carga
    df_bares = cargar_csv(ruta_bares)
    df_usuarios = cargar_csv(ruta_usuarios)
    df_opiniones = cargar_csv(ruta_opiniones)
    df_cp = cargar_csv(ruta_cp)
    df_favoritos = cargar_csv(ruta_favoritos)

    # Mapas y agrupaciones
    mapa_cp = construir_mapa_cp(df_cp)
    mapa_usernames = construir_mapa_usernames(df_usuarios)

    opiniones_por_bar = construir_opiniones_por_bar(df_opiniones, mapa_usernames)
    opiniones_por_usuario = construir_opiniones_por_usuario(df_opiniones)

    favoritos_por_usuario = construir_favoritos_por_usuario(df_favoritos)
    favoritos_por_bar = construir_favoritos_por_bar(df_favoritos)

    # Enriquecimiento
    bares_enriquecidos = enriquecer_bares(
        df_bares,
        mapa_cp,
        opiniones_por_bar,
        favoritos_por_bar
    )

    usuarios_enriquecidos = enriquecer_usuarios(
        df_usuarios,
        mapa_cp,
        opiniones_por_usuario,
        favoritos_por_usuario
    )

    # Guardado
    guardar_json(bares_enriquecidos, ruta_bares_json)
    guardar_json(usuarios_enriquecidos, ruta_usuarios_json)


if __name__ == "__main__":
    main()