from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

# Añadir la raíz del proyecto al path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import backend.recomender_refresh as rr
from src.models.content_based import ContentBasedRecommender
from src.models.collaborative_bpr import CollaborativeBPR
from src.models.hybrid_switching import HybridRecommender
from src.models.busqueda_semantica_bares import BuscadorSemanticoBares

app = Flask(__name__)
CORS(app)

WEB_DIR = ROOT_DIR / "web"
DATA_DIR = ROOT_DIR / "data"

USERS_CSV = Path("data/jaen/usuarios_finales.csv")
BARES_CSV = Path("data/jaen/bares_finales.csv")
OPINIONES_CSV = Path("data/jaen/opiniones.csv")
FAVORITOS_CSV = Path("data/jaen/favoritos.csv")
CP_JAEN_CSV = Path("data/jaen/cp_jaen.csv")

# =========================
# RECOMENDADOR HÍBRIDO
# =========================
cb_model = None
bpr_model = None
hybrid_model = None
semantic_search_model = None


def inicializar_recomendador():
    global cb_model, bpr_model, hybrid_model, semantic_search_model

    cb_model = ContentBasedRecommender(
        bars_csv="data/jaen/bares_finales.csv",
        opinions_csv="data/jaen/opiniones.csv",
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
    bpr_model.fit(
        "data/jaen/opiniones.csv",
        bars_csv="data/jaen/bares_finales.csv"
    )

    hybrid_model = HybridRecommender(
        content_model=cb_model,
        collaborative_model=bpr_model,
        usuarios_csv="data/jaen/usuarios_finales.csv"
    )

    semantic_search_model = BuscadorSemanticoBares(
        bars_csv="data/jaen/bares_finales.csv",
        opinions_csv="data/jaen/opiniones.csv",
        bar_embeddings_path="data/jaen/embeddings/embeddings_bares.npy",
        bar_index_path="data/jaen/embeddings/embeddings_index.csv"
    )

    rr.lanzar_worker_bpr(sys.modules[__name__])


# =========================
# USUARIOS
# =========================
def cargar_usuarios():
    if not USERS_CSV.exists():
        columnas = [
            "user_id",
            "username",
            "preferencias",
            "email",
            "n_interacciones",
            "top_types",
            "avg_price_level_likes",
            "password",
            "fecha_nacimiento"
        ]
        df_vacio = pd.DataFrame(columns=columnas)
        USERS_CSV.parent.mkdir(parents=True, exist_ok=True)
        df_vacio.to_csv(USERS_CSV, index=False, encoding="utf-8")
        return df_vacio

    return pd.read_csv(USERS_CSV)


def guardar_usuarios(df):
    df.to_csv(USERS_CSV, index=False, encoding="utf-8")


# =========================
# BARES
# =========================
def cargar_bares():
    if not BARES_CSV.exists():
        columnas = [
            "placeID",
            "nombre",
            "lat",
            "lon",
            "cod_postal",
            "calle",
            "val_media",
            "num_val",
            "price_level",
            "website",
            "opening_hours_weekday_text",
            "types",
            "texto_semantico",
            "photo",
            "descripcion"
        ]
        df_vacio = pd.DataFrame(columns=columnas)
        BARES_CSV.parent.mkdir(parents=True, exist_ok=True)
        df_vacio.to_csv(BARES_CSV, index=False, encoding="utf-8")
        return df_vacio

    return pd.read_csv(BARES_CSV)


def cargar_codigos_postales():
    if not CP_JAEN_CSV.exists():
        columnas = ["postal_code", "ciudad", "provincia", "pais"]
        df_vacio = pd.DataFrame(columns=columnas)
        CP_JAEN_CSV.parent.mkdir(parents=True, exist_ok=True)
        df_vacio.to_csv(CP_JAEN_CSV, index=False, encoding="utf-8")
        return df_vacio

    return pd.read_csv(CP_JAEN_CSV)


# =========================
# OPINIONES
# =========================
def cargar_opiniones():
    if not OPINIONES_CSV.exists():
        columnas = ["placeID", "user_id", "rating", "text", "fecha_publicacion"]
        df_vacio = pd.DataFrame(columns=columnas)
        OPINIONES_CSV.parent.mkdir(parents=True, exist_ok=True)
        df_vacio.to_csv(OPINIONES_CSV, index=False, encoding="utf-8")
        return df_vacio

    return pd.read_csv(OPINIONES_CSV)


def guardar_opiniones(df):
    df.to_csv(OPINIONES_CSV, index=False, encoding="utf-8")


# =========================
# FAVORITOS
# =========================
def cargar_favoritos():
    if not FAVORITOS_CSV.exists():
        columnas = ["user_id", "placeID"]
        df_vacio = pd.DataFrame(columns=columnas)
        FAVORITOS_CSV.parent.mkdir(parents=True, exist_ok=True)
        df_vacio.to_csv(FAVORITOS_CSV, index=False, encoding="utf-8")
        return df_vacio

    return pd.read_csv(FAVORITOS_CSV)


def guardar_favoritos(df):
    df.to_csv(FAVORITOS_CSV, index=False, encoding="utf-8")


# =========================
# HELPERS
# =========================
def normalizar_texto(valor):
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def limpiar_opcion(valor):
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def obtener_valor_numerico(valor, default=None):
    try:
        if pd.isna(valor):
            return default
        return float(valor)
    except Exception:
        return default


def contar_palabras(texto):
    texto = normalizar_texto(texto)
    if texto == "":
        return 0
    return len(texto.split())


def normalizar_tipo_filtro(valor):
    valor = limpiar_opcion(valor).lower()

    equivalencias = {
        "restaurante": "restaurant",
        "restaurant": "restaurant",
        "bar": "bar",
        "taberna": "taberna",
        "cafeteria": "cafeteria",
        "cafetería": "cafeteria",
        "meson": "meson",
        "mesón": "meson"
    }

    return equivalencias.get(valor, valor)


def coincide_tipo_bar(types_text, tipo_buscado):
    types_text = limpiar_opcion(types_text).lower().replace("|", " ")
    tipo_buscado = normalizar_tipo_filtro(tipo_buscado)

    if tipo_buscado == "":
        return True

    return tipo_buscado in types_text


def normalizar_precio_filtro(valor):
    valor = limpiar_opcion(valor).lower()

    mapa = {
        "economico": "1-10€",
        "económico": "1-10€",
        "medio": "10-20€",
        "alto": "20-30€"
    }

    return mapa.get(valor, valor)


def ordenar_bares_por_criterio(df, order_value):
    if df.empty:
        return df

    order_value = limpiar_opcion(order_value)

    if order_value == "valoracion":
        if "val_media" in df.columns:
            df = df.copy()
            df["val_media_num"] = pd.to_numeric(df["val_media"], errors="coerce").fillna(-1)
            return df.sort_values(by="val_media_num", ascending=False).drop(columns=["val_media_num"])

    if order_value in ["precioAsc", "precioDesc"]:
        df = df.copy()

        def peso_precio(x):
            x = limpiar_opcion(x)
            if x == "1-10€":
                return 1
            if x == "10-20€":
                return 2
            if x == "20-30€":
                return 3
            return 999

        df["precio_orden"] = df["price_level"].apply(peso_precio)
        asc = order_value == "precioAsc"
        return df.sort_values(by="precio_orden", ascending=asc).drop(columns=["precio_orden"])

    return df


def enriquecer_bares_con_ciudad(df_bares):
    if df_bares.empty:
        df = df_bares.copy()
        df["ciudad"] = ""
        return df

    df = df_bares.copy()

    if "cod_postal" not in df.columns:
        df["ciudad"] = ""
        return df

    df_cp = cargar_codigos_postales()

    if df_cp.empty or "postal_code" not in df_cp.columns or "ciudad" not in df_cp.columns:
        df["ciudad"] = ""
        return df

    df["cod_postal_num"] = pd.to_numeric(df["cod_postal"], errors="coerce")
    df_cp["postal_code_num"] = pd.to_numeric(df_cp["postal_code"], errors="coerce")

    df["cod_postal_num"] = df["cod_postal_num"].astype("Int64")
    df_cp["postal_code_num"] = df_cp["postal_code_num"].astype("Int64")

    df_cp = df_cp.copy()
    df_cp["ciudad"] = df_cp["ciudad"].fillna("").astype(str).str.strip()

    # Si hubiera duplicados en postal_code, nos quedamos con el primero
    df_cp_unico = (
        df_cp.dropna(subset=["postal_code_num"])
        .drop_duplicates(subset=["postal_code_num"], keep="first")
        [["postal_code_num", "ciudad"]]
        .copy()
    )

    df = df.merge(
        df_cp_unico,
        left_on="cod_postal_num",
        right_on="postal_code_num",
        how="left"
    )

    df["ciudad"] = df["ciudad"].fillna("").astype(str).str.strip()

    df = df.drop(columns=["cod_postal_num", "postal_code_num"], errors="ignore")

    return df


def construir_bar_json_desde_busqueda(bar):
    return {
        "placeID": int(bar["placeID"]) if bar.get("placeID") is not None else None,
        "nombre": normalizar_texto(bar.get("nombre", "")),
        "photo": normalizar_texto(bar.get("photo", "")),
        "types": normalizar_texto(bar.get("types", "")),
        "types_legible": normalizar_texto(bar.get("types_legible", "")),
        "price_level": normalizar_texto(bar.get("price_level", "")),
        "val_media": obtener_valor_numerico(bar.get("val_media"), None),
        "num_val": obtener_valor_numerico(bar.get("num_val"), None),
        "descripcion": normalizar_texto(bar.get("descripcion", "")),
        "texto_semantico": normalizar_texto(bar.get("texto_semantico", "")),
        "opening_hours_weekday_text": normalizar_texto(bar.get("opening_hours_weekday_text", "")),
        "opening_hours_parseado": bar.get("opening_hours_parseado", []),
        "calle": normalizar_texto(bar.get("calle", "")),
        "lat": obtener_valor_numerico(bar.get("lat"), None),
        "lon": obtener_valor_numerico(bar.get("lon"), None),
        "cod_postal": obtener_valor_numerico(bar.get("cod_postal"), None),
        "website": normalizar_texto(bar.get("website", "")),
        "score_semantico": obtener_valor_numerico(bar.get("score_semantico"), None),
        "score_rerank": obtener_valor_numerico(bar.get("score_rerank"), None),
        "zona": normalizar_texto(bar.get("ciudad", "")),
        "ciudad": normalizar_texto(bar.get("ciudad", "")),
        "opiniones": bar.get("opiniones", [])
    }


# =========================
# RUTA BASE
# =========================
@app.route("/", methods=["GET"])
def home():
    return redirect("/web/html/inicio.html")


@app.route("/web/<path:filename>")
def servir_web(filename):
    return send_from_directory(WEB_DIR, filename)


@app.route("/data/<path:filename>")
def servir_data(filename):
    return send_from_directory(DATA_DIR, filename)


# =========================
# LOGIN
# =========================
@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()

        username = normalizar_texto(data.get("username", "")).lower()
        password = normalizar_texto(data.get("password", ""))

        if username == "" or password == "":
            return jsonify({
                "ok": False,
                "mensaje": "Username y password son obligatorios."
            }), 400

        df = cargar_usuarios()
        df["username"] = df["username"].fillna("").astype(str).str.strip()
        df["password"] = df["password"].fillna("").astype(str)
        df["email"] = df["email"].fillna("").astype(str).str.strip()

        usuario = df[
            (df["username"].str.lower() == username) &
            (df["password"] == password)
        ]

        if usuario.empty:
            return jsonify({
                "ok": False,
                "mensaje": "Credenciales incorrectas."
            }), 401

        fila = usuario.iloc[0]

        return jsonify({
            "ok": True,
            "mensaje": "Login correcto.",
            "usuario": {
                "user_id": int(fila["user_id"]),
                "username": fila["username"],
                "email": normalizar_texto(fila.get("email", "")),
                "fecha_nacimiento": normalizar_texto(fila.get("fecha_nacimiento", ""))
            }
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "mensaje": f"Error interno en login: {str(e)}"
        }), 500


# =========================
# REGISTER
# =========================
@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()

        username = normalizar_texto(data.get("username", ""))
        email = normalizar_texto(data.get("email", ""))
        password = normalizar_texto(data.get("password", ""))
        fecha_nacimiento = normalizar_texto(data.get("fecha_nacimiento", ""))

        if username == "" or email == "" or password == "":
            return jsonify({
                "ok": False,
                "mensaje": "Username, email y password son obligatorios."
            }), 400

        if len(password) < 6:
            return jsonify({
                "ok": False,
                "mensaje": "La contraseña debe tener al menos 6 caracteres."
            }), 400

        df = cargar_usuarios()
        df["username"] = df["username"].fillna("").astype(str).str.strip()
        df["email"] = df["email"].fillna("").astype(str).str.strip()

        existe_username = df["username"].str.lower() == username.lower()
        if existe_username.any():
            return jsonify({
                "ok": False,
                "mensaje": "Ese nombre de usuario ya existe."
            }), 409

        existe_email = df["email"].str.lower() == email.lower()
        if existe_email.any():
            return jsonify({
                "ok": False,
                "mensaje": "Ese correo electrónico ya está registrado."
            }), 409

        if df.empty:
            nuevo_user_id = 0
        else:
            nuevo_user_id = int(
                pd.to_numeric(df["user_id"], errors="coerce").fillna(-1).max()
            ) + 1

        nueva_fila = {
            "user_id": nuevo_user_id,
            "username": username,
            "preferencias": "",
            "email": email,
            "n_interacciones": 0,
            "top_types": "",
            "avg_price_level_likes": "",
            "password": password,
            "fecha_nacimiento": fecha_nacimiento
        }

        df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
        guardar_usuarios(df)

        return jsonify({
            "ok": True,
            "mensaje": "Usuario registrado correctamente.",
            "usuario": {
                "user_id": nuevo_user_id,
                "username": username,
                "email": email,
                "fecha_nacimiento": fecha_nacimiento
            }
        }), 201

    except Exception as e:
        return jsonify({
            "ok": False,
            "mensaje": f"Error interno en register: {str(e)}"
        }), 500


# =========================
# GET RECOMENDACIONES DE UN USUARIO
# =========================
@app.route("/recomendaciones/<int:user_id>", methods=["GET"])
def get_recomendaciones_usuario(user_id):
    try:
        limit = request.args.get("limit", default=20, type=int)
        if limit is None or limit <= 0:
            limit = 20

        df_usuarios = cargar_usuarios()
        df_usuarios["user_id"] = pd.to_numeric(df_usuarios["user_id"], errors="coerce")

        if not (df_usuarios["user_id"] == user_id).any():
            return jsonify({
                "ok": False,
                "mensaje": "El usuario no existe."
            }), 404

        df_bares = cargar_bares()
        if df_bares.empty:
            return jsonify({
                "ok": True,
                "mensaje": "No hay bares disponibles.",
                "recomendaciones": []
            }), 200

        df_bares = enriquecer_bares_con_ciudad(df_bares)

        df_bares["placeID"] = pd.to_numeric(df_bares["placeID"], errors="coerce")
        df_bares = df_bares.dropna(subset=["placeID"]).copy()
        df_bares["placeID"] = df_bares["placeID"].astype(int)

        resultado = hybrid_model.recommend(user_id=user_id, k=limit, exclude_seen=True)
        recomendaciones = resultado.get("recomendaciones", [])

        if len(recomendaciones) == 0:
            return jsonify({
                "ok": True,
                "mensaje": resultado.get("mensaje", "No hay recomendaciones para este usuario"),
                "estrategia": resultado.get("estrategia", "none"),
                "n_interacciones": resultado.get("n_interacciones", 0),
                "recomendaciones": []
            }), 200

        recs_df = pd.DataFrame(recomendaciones)
        recs_df["placeID"] = pd.to_numeric(recs_df["placeID"], errors="coerce")
        recs_df = recs_df.dropna(subset=["placeID"]).copy()
        recs_df["placeID"] = recs_df["placeID"].astype(int)

        recs_df = recs_df.merge(
            df_bares[
                [
                    "placeID",
                    "nombre",
                    "photo",
                    "types",
                    "price_level",
                    "val_media",
                    "descripcion",
                    "opening_hours_weekday_text",
                    "calle",
                    "ciudad"
                ]
            ],
            on="placeID",
            how="left",
            suffixes=("", "_bar")
        )

        recomendaciones_json = []
        for _, fila in recs_df.iterrows():
            recomendaciones_json.append({
                "placeID": int(fila["placeID"]),
                "nombre": normalizar_texto(fila.get("nombre", "")),
                "photo": normalizar_texto(fila.get("photo", "")),
                "types": normalizar_texto(fila.get("types", "")),
                "price_level": normalizar_texto(fila.get("price_level", "")),
                "val_media": obtener_valor_numerico(fila.get("val_media"), None),
                "descripcion": normalizar_texto(fila.get("descripcion", "")),
                "opening_hours_weekday_text": normalizar_texto(fila.get("opening_hours_weekday_text", "")),
                "calle": normalizar_texto(fila.get("calle", "")),
                "zona": normalizar_texto(fila.get("ciudad", "")),
                "ciudad": normalizar_texto(fila.get("ciudad", "")),
                "score_final": obtener_valor_numerico(fila.get("score_final"), None),
                "score_cb": obtener_valor_numerico(fila.get("score_cb"), None),
                "score_bpr": obtener_valor_numerico(fila.get("score_bpr"), None)
            })

        return jsonify({
            "ok": True,
            "mensaje": resultado.get("mensaje", ""),
            "estrategia": resultado.get("estrategia", ""),
            "n_interacciones": resultado.get("n_interacciones", 0),
            "recomendaciones": recomendaciones_json
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "mensaje": f"Error obteniendo recomendaciones: {str(e)}"
        }), 500


@app.route("/recomendaciones-invitado", methods=["GET"])
def get_recomendaciones_invitado():
    try:
        limit = request.args.get("limit", default=20, type=int)
        if limit is None or limit <= 0:
            limit = 20

        df_bares = cargar_bares()
        if df_bares.empty:
            return jsonify({
                "ok": True,
                "mensaje": "No hay bares disponibles.",
                "recomendaciones": []
            }), 200

        df_bares = enriquecer_bares_con_ciudad(df_bares)

        if "placeID" in df_bares.columns:
            df_bares["placeID"] = pd.to_numeric(df_bares["placeID"], errors="coerce")
            df_bares = df_bares.dropna(subset=["placeID"]).copy()
            df_bares["placeID"] = df_bares["placeID"].astype(int)

        if "val_media" in df_bares.columns:
            df_bares["val_media_num"] = pd.to_numeric(df_bares["val_media"], errors="coerce").fillna(0)
        else:
            df_bares["val_media_num"] = 0

        if "num_val" in df_bares.columns:
            df_bares["num_val_num"] = pd.to_numeric(df_bares["num_val"], errors="coerce").fillna(0)
        else:
            df_bares["num_val_num"] = 0

        df_bares = df_bares.sort_values(
            by=["val_media_num", "num_val_num"],
            ascending=[False, False]
        ).head(limit).copy()

        recomendaciones = []
        for _, fila in df_bares.iterrows():
            recomendaciones.append({
                "placeID": int(fila["placeID"]),
                "nombre": normalizar_texto(fila.get("nombre", "")),
                "photo": normalizar_texto(fila.get("photo", "")),
                "types": normalizar_texto(fila.get("types", "")),
                "price_level": normalizar_texto(fila.get("price_level", "")),
                "val_media": obtener_valor_numerico(fila.get("val_media"), None),
                "num_val": obtener_valor_numerico(fila.get("num_val"), None),
                "descripcion": normalizar_texto(fila.get("descripcion", "")),
                "texto_semantico": normalizar_texto(fila.get("texto_semantico", "")),
                "opening_hours_weekday_text": normalizar_texto(fila.get("opening_hours_weekday_text", "")),
                "calle": normalizar_texto(fila.get("calle", "")),
                "zona": normalizar_texto(fila.get("ciudad", "")),
                "ciudad": normalizar_texto(fila.get("ciudad", ""))
            })

        return jsonify({
            "ok": True,
            "mensaje": "No has iniciado sesión o no tienes historial suficiente. Te mostramos recomendaciones generales.",
            "recomendaciones": recomendaciones
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "mensaje": f"Error obteniendo recomendaciones de invitado: {str(e)}"
        }), 500

# =========================
# GET OPINIONES DE UN BAR
# =========================
@app.route("/opiniones/<int:place_id>", methods=["GET"])
def get_opiniones_bar(place_id):
    try:
        df_opiniones = cargar_opiniones()
        df_usuarios = cargar_usuarios()

        if df_opiniones.empty:
            return jsonify({
                "ok": True,
                "opiniones": []
            }), 200

        df_opiniones["placeID"] = pd.to_numeric(df_opiniones["placeID"], errors="coerce")
        df_opiniones["user_id"] = pd.to_numeric(df_opiniones["user_id"], errors="coerce")
        df_opiniones["rating"] = pd.to_numeric(df_opiniones["rating"], errors="coerce")

        df_usuarios["user_id"] = pd.to_numeric(df_usuarios["user_id"], errors="coerce")
        df_usuarios["username"] = df_usuarios["username"].fillna("").astype(str).str.strip()

        opiniones_bar = df_opiniones[df_opiniones["placeID"] == place_id].copy()

        if opiniones_bar.empty:
            return jsonify({
                "ok": True,
                "opiniones": []
            }), 200

        opiniones_bar = opiniones_bar.merge(
            df_usuarios[["user_id", "username"]],
            on="user_id",
            how="left"
        )

        opiniones_bar["username"] = opiniones_bar["username"].fillna("Usuario")

        if "fecha_publicacion" in opiniones_bar.columns:
            opiniones_bar = opiniones_bar.sort_values(
                by="fecha_publicacion",
                ascending=False
            )

        opiniones_json = []
        for _, fila in opiniones_bar.iterrows():
            opiniones_json.append({
                "placeID": int(fila["placeID"]),
                "user_id": int(fila["user_id"]),
                "username": fila["username"],
                "rating": int(fila["rating"]),
                "text": normalizar_texto(fila.get("text", "")),
                "fecha_publicacion": normalizar_texto(fila.get("fecha_publicacion", ""))
            })

        return jsonify({
            "ok": True,
            "opiniones": opiniones_json
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "mensaje": f"Error obteniendo opiniones: {str(e)}"
        }), 500


# =========================
# GET OPINIONES DE UN USUARIO
# =========================
@app.route("/opiniones/usuario/<int:user_id>", methods=["GET"])
def get_opiniones_usuario(user_id):
    try:
        df_opiniones = cargar_opiniones()
        df_usuarios = cargar_usuarios()

        if df_opiniones.empty:
            return jsonify({
                "ok": True,
                "opiniones": []
            }), 200

        df_opiniones["placeID"] = pd.to_numeric(df_opiniones["placeID"], errors="coerce")
        df_opiniones["user_id"] = pd.to_numeric(df_opiniones["user_id"], errors="coerce")
        df_opiniones["rating"] = pd.to_numeric(df_opiniones["rating"], errors="coerce")

        df_usuarios["user_id"] = pd.to_numeric(df_usuarios["user_id"], errors="coerce")
        df_usuarios["username"] = df_usuarios["username"].fillna("").astype(str).str.strip()

        opiniones_usuario = df_opiniones[df_opiniones["user_id"] == user_id].copy()

        if opiniones_usuario.empty:
            return jsonify({
                "ok": True,
                "opiniones": []
            }), 200

        opiniones_usuario = opiniones_usuario.merge(
            df_usuarios[["user_id", "username"]],
            on="user_id",
            how="left"
        )

        opiniones_usuario["username"] = opiniones_usuario["username"].fillna("Usuario")

        if "fecha_publicacion" in opiniones_usuario.columns:
            opiniones_usuario = opiniones_usuario.sort_values(
                by="fecha_publicacion",
                ascending=False
            )

        opiniones_json = []
        for _, fila in opiniones_usuario.iterrows():
            opiniones_json.append({
                "placeID": int(fila["placeID"]),
                "user_id": int(fila["user_id"]),
                "username": fila["username"],
                "rating": int(fila["rating"]),
                "text": normalizar_texto(fila.get("text", "")),
                "fecha_publicacion": normalizar_texto(fila.get("fecha_publicacion", ""))
            })

        return jsonify({
            "ok": True,
            "opiniones": opiniones_json
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "mensaje": f"Error obteniendo opiniones del usuario: {str(e)}"
        }), 500


# =========================
# POST NUEVA OPINIÓN
# =========================
@app.route("/opiniones", methods=["POST"])
def crear_opinion():
    try:
        data = request.get_json()

        place_id = data.get("placeID")
        user_id = data.get("user_id")
        rating = data.get("rating")
        text = normalizar_texto(data.get("text", ""))

        if place_id is None or user_id is None or rating is None or text == "":
            return jsonify({
                "ok": False,
                "mensaje": "placeID, user_id, rating y text son obligatorios."
            }), 400

        try:
            place_id = int(place_id)
            user_id = int(user_id)
            rating = int(rating)
        except ValueError:
            return jsonify({
                "ok": False,
                "mensaje": "placeID, user_id y rating deben ser numéricos."
            }), 400

        if rating < 1 or rating > 5:
            return jsonify({
                "ok": False,
                "mensaje": "La valoración debe estar entre 1 y 5."
            }), 400

        df_usuarios = cargar_usuarios()
        df_usuarios["user_id"] = pd.to_numeric(df_usuarios["user_id"], errors="coerce")

        if not (df_usuarios["user_id"] == user_id).any():
            return jsonify({
                "ok": False,
                "mensaje": "El usuario no existe."
            }), 404

        df_opiniones = cargar_opiniones()

        ## Si un usuario ya ha añadido una opinion no deja añadir mas
        df_opiniones["placeID"] = pd.to_numeric(df_opiniones["placeID"], errors="coerce")
        df_opiniones["user_id"] = pd.to_numeric(df_opiniones["user_id"], errors="coerce")

        ya_existe = (
            (df_opiniones["placeID"] == place_id) &
            (df_opiniones["user_id"] == user_id)
        )

        if ya_existe.any():
            return jsonify({
                "ok": False,
                "mensaje": "Ya has escrito una opinión sobre este bar."
            }), 409
       
        ##
        nueva_fila = {
            "placeID": place_id,
            "user_id": user_id,
            "rating": rating,
            "text": text,
            "fecha_publicacion": datetime.utcnow().isoformat() + "Z"
        }

        df_opiniones = pd.concat(
            [df_opiniones, pd.DataFrame([nueva_fila])],
            ignore_index=True
        )

        guardar_opiniones(df_opiniones)

        rr.refrescar_recomendacion_local(sys.modules[__name__], user_id, place_id)

        return jsonify({
            "ok": True,
            "mensaje": "Opinión guardada correctamente."
        }), 201

    except Exception as e:
        return jsonify({
            "ok": False,
            "mensaje": f"Error creando opinión: {str(e)}"
        }), 500


# =========================
# GET FAVORITOS DE UN USUARIO
# =========================
@app.route("/favoritos/<int:user_id>", methods=["GET"])
def get_favoritos_usuario(user_id):
    try:
        df_favoritos = cargar_favoritos()

        if df_favoritos.empty:
            return jsonify({
                "ok": True,
                "favoritos": []
            }), 200

        df_favoritos["user_id"] = pd.to_numeric(df_favoritos["user_id"], errors="coerce")
        df_favoritos["placeID"] = pd.to_numeric(df_favoritos["placeID"], errors="coerce")

        favoritos_usuario = df_favoritos[
            df_favoritos["user_id"] == user_id
        ]["placeID"].dropna().astype(int).tolist()

        return jsonify({
            "ok": True,
            "favoritos": favoritos_usuario
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "mensaje": f"Error obteniendo favoritos: {str(e)}"
        }), 500


# =========================
# POST FAVORITO
# =========================
@app.route("/favoritos", methods=["POST"])
def crear_favorito():
    try:
        data = request.get_json()

        user_id = data.get("user_id")
        place_id = data.get("placeID")

        if user_id is None or place_id is None:
            return jsonify({
                "ok": False,
                "mensaje": "user_id y placeID son obligatorios."
            }), 400

        try:
            user_id = int(user_id)
            place_id = int(place_id)
        except ValueError:
            return jsonify({
                "ok": False,
                "mensaje": "user_id y placeID deben ser numéricos."
            }), 400

        df_usuarios = cargar_usuarios()
        df_usuarios["user_id"] = pd.to_numeric(df_usuarios["user_id"], errors="coerce")

        if not (df_usuarios["user_id"] == user_id).any():
            return jsonify({
                "ok": False,
                "mensaje": "El usuario no existe."
            }), 404

        df_favoritos = cargar_favoritos()

        if not df_favoritos.empty:
            df_favoritos["user_id"] = pd.to_numeric(df_favoritos["user_id"], errors="coerce")
            df_favoritos["placeID"] = pd.to_numeric(df_favoritos["placeID"], errors="coerce")

            existe = (
                (df_favoritos["user_id"] == user_id) &
                (df_favoritos["placeID"] == place_id)
            )

            if existe.any():
                return jsonify({
                    "ok": True,
                    "mensaje": "El favorito ya existía."
                }), 200

        nueva_fila = {
            "user_id": user_id,
            "placeID": place_id
        }

        df_favoritos = pd.concat(
            [df_favoritos, pd.DataFrame([nueva_fila])],
            ignore_index=True
        )

        guardar_favoritos(df_favoritos)

        return jsonify({
            "ok": True,
            "mensaje": "Favorito guardado correctamente."
        }), 201

    except Exception as e:
        return jsonify({
            "ok": False,
            "mensaje": f"Error creando favorito: {str(e)}"
        }), 500


# =========================
# DELETE FAVORITO
# =========================
@app.route("/favoritos", methods=["DELETE"])
def eliminar_favorito():
    try:
        data = request.get_json()

        user_id = data.get("user_id")
        place_id = data.get("placeID")

        if user_id is None or place_id is None:
            return jsonify({
                "ok": False,
                "mensaje": "user_id y placeID son obligatorios."
            }), 400

        try:
            user_id = int(user_id)
            place_id = int(place_id)
        except ValueError:
            return jsonify({
                "ok": False,
                "mensaje": "user_id y placeID deben ser numéricos."
            }), 400

        df_favoritos = cargar_favoritos()

        if df_favoritos.empty:
            return jsonify({
                "ok": True,
                "mensaje": "No había favoritos que eliminar."
            }), 200

        df_favoritos["user_id"] = pd.to_numeric(df_favoritos["user_id"], errors="coerce")
        df_favoritos["placeID"] = pd.to_numeric(df_favoritos["placeID"], errors="coerce")

        df_favoritos = df_favoritos[
            ~(
                (df_favoritos["user_id"] == user_id) &
                (df_favoritos["placeID"] == place_id)
            )
        ].copy()

        guardar_favoritos(df_favoritos)

        return jsonify({
            "ok": True,
            "mensaje": "Favorito eliminado correctamente."
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "mensaje": f"Error eliminando favorito: {str(e)}"
        }), 500


# =========================
# POST BÚSQUEDA SEMÁNTICA POR DESCRIPCIÓN
# =========================
@app.route("/busqueda-semantic", methods=["POST"])
def busqueda_semantica():
    try:
        global semantic_search_model

        data = request.get_json(silent=True) or {}

        query = normalizar_texto(data.get("query", ""))
        top_k = data.get("top_k", 20)
        user_id = data.get("user_id", None)

        if query == "":
            return jsonify({
                "ok": False,
                "mensaje": "La consulta no puede estar vacía."
            }), 400

        if contar_palabras(query) < 20:
            return jsonify({
                "ok": False,
                "mensaje": "Debes escribir al menos 20 palabras para realizar la búsqueda por descripción."
            }), 400

        try:
            top_k = int(top_k)
        except Exception:
            top_k = 20

        if top_k <= 0:
            top_k = 20

        if user_id is not None:
            try:
                user_id = int(user_id)
                df_usuarios = cargar_usuarios()
                df_usuarios["user_id"] = pd.to_numeric(df_usuarios["user_id"], errors="coerce")

                if not (df_usuarios["user_id"] == user_id).any():
                    return jsonify({
                        "ok": False,
                        "mensaje": "El usuario no existe."
                    }), 404
            except Exception:
                return jsonify({
                    "ok": False,
                    "mensaje": "user_id no válido."
                }), 400

        if semantic_search_model is None:
            return jsonify({
                "ok": False,
                "mensaje": "El buscador semántico no está inicializado."
            }), 500

        resultado = semantic_search_model.buscar(
            frase_usuario=query,
            top_k=top_k,
            max_opiniones=5
        )

        bares = resultado.get("resultados", [])
        recomendaciones_json = [construir_bar_json_desde_busqueda(bar) for bar in bares]

        restricciones = resultado.get("restricciones_detectadas", {})
        cocina = restricciones.get("cocina")
        dia = restricciones.get("dia")
        hora_min = restricciones.get("hora_minutos")
        economico = restricciones.get("economico")
        reservas = restricciones.get("reservas")

        detalles_restricciones = []
        if cocina:
            detalles_restricciones.append(f"cocina={cocina}")
        if dia:
            detalles_restricciones.append(f"día={dia}")
        if hora_min is not None:
            hora = hora_min // 60
            minutos = hora_min % 60
            detalles_restricciones.append(f"hora={hora:02d}:{minutos:02d}")
        if economico:
            detalles_restricciones.append("económico")
        if reservas:
            detalles_restricciones.append("reservas")

        if len(detalles_restricciones) > 0:
            mensaje = (
                f"Se han encontrado {len(recomendaciones_json)} bares a partir de tu descripción. "
                f"Restricciones detectadas: {', '.join(detalles_restricciones)}."
            )
        else:
            mensaje = f"Se han encontrado {len(recomendaciones_json)} bares a partir de tu descripción."

        return jsonify({
            "ok": True,
            "modo": "descripcion",
            "mensaje": mensaje,
            "consulta": resultado.get("consulta_usuario", query),
            "modelo_embedding": resultado.get("modelo_embedding", ""),
            "restricciones_detectadas": restricciones,
            "recomendaciones": recomendaciones_json
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "mensaje": f"Error en búsqueda semántica: {str(e)}"
        }), 500


# =========================
# GET OPCIONES DE FILTROS
# =========================
@app.route("/filtros/opciones", methods=["GET"])
def get_opciones_filtros():
    try:
        df_bares = cargar_bares()

        if df_bares.empty:
            return jsonify({
                "ok": True,
                "tipos": [],
                "precios": [],
                "zonas": [],
                "mensaje": "No hay bares disponibles."
            }), 200

        df_bares = enriquecer_bares_con_ciudad(df_bares)

        tipos = set()
        if "types" in df_bares.columns:
            for valor in df_bares["types"].fillna("").astype(str):
                for parte in valor.split("|"):
                    parte = parte.strip().lower()
                    if parte != "":
                        tipos.add(parte)

        precios = []
        if "price_level" in df_bares.columns:
            precios = sorted(
                [p for p in df_bares["price_level"].fillna("").astype(str).str.strip().unique().tolist() if p != ""]
            )

        zonas = []
        if "ciudad" in df_bares.columns:
            zonas = sorted(
                [z for z in df_bares["ciudad"].fillna("").astype(str).str.strip().unique().tolist() if z != ""]
            )

        return jsonify({
            "ok": True,
            "tipos": sorted(list(tipos)),
            "precios": precios,
            "zonas": zonas,
            "columna_localidad": "ciudad",
            "mensaje": ""
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "mensaje": f"Error obteniendo opciones de filtros: {str(e)}"
        }), 500


# =========================
# POST BÚSQUEDA POR FILTROS
# =========================
@app.route("/buscar/filtros", methods=["POST"])
def buscar_por_filtros():
    try:
        data = request.get_json(silent=True) or {}

        tipo = limpiar_opcion(data.get("type", ""))
        zona = limpiar_opcion(data.get("zone", ""))
        precio = limpiar_opcion(data.get("price", ""))
        order_value = limpiar_opcion(data.get("order", "relevancia"))
        limit = data.get("limit", 50)

        try:
            limit = int(limit)
        except Exception:
            limit = 50

        if limit <= 0:
            limit = 50

        df = cargar_bares()

        if df.empty:
            return jsonify({
                "ok": True,
                "mensaje": "No hay bares disponibles.",
                "recomendaciones": []
            }), 200

        df = enriquecer_bares_con_ciudad(df)

        if "placeID" in df.columns:
            df["placeID"] = pd.to_numeric(df["placeID"], errors="coerce")
            df = df.dropna(subset=["placeID"]).copy()
            df["placeID"] = df["placeID"].astype(int)

        if tipo != "" and "types" in df.columns:
            df = df[df["types"].apply(lambda x: coincide_tipo_bar(x, tipo))].copy()

        if precio != "" and "price_level" in df.columns:
            precio_real = normalizar_precio_filtro(precio)
            df = df[df["price_level"].fillna("").astype(str).str.strip() == precio_real].copy()

        if zona != "":
            df = df[
                df["ciudad"].fillna("").astype(str).str.strip().str.lower() == zona.lower()
            ].copy()

        df = ordenar_bares_por_criterio(df, order_value)
        df = df.head(limit).copy()

        recomendaciones = []
        for _, fila in df.iterrows():
            recomendaciones.append({
                "placeID": int(fila["placeID"]),
                "nombre": normalizar_texto(fila.get("nombre", "")),
                "photo": normalizar_texto(fila.get("photo", "")),
                "types": normalizar_texto(fila.get("types", "")),
                "price_level": normalizar_texto(fila.get("price_level", "")),
                "val_media": obtener_valor_numerico(fila.get("val_media"), None),
                "descripcion": normalizar_texto(fila.get("descripcion", "")),
                "texto_semantico": normalizar_texto(fila.get("texto_semantico", "")),
                "opening_hours_weekday_text": normalizar_texto(fila.get("opening_hours_weekday_text", "")),
                "calle": normalizar_texto(fila.get("calle", "")),
                "zona": normalizar_texto(fila.get("ciudad", "")),
                "ciudad": normalizar_texto(fila.get("ciudad", ""))
            })

        return jsonify({
            "ok": True,
            "mensaje": f"Se han encontrado {len(recomendaciones)} bares tras aplicar los filtros.",
            "recomendaciones": recomendaciones,
            "columna_localidad": "ciudad"
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "mensaje": f"Error buscando por filtros: {str(e)}"
        }), 500

# =========================
# POST BÚSQUEDA POR NOMBRE
# =========================
@app.route("/buscar/nombre", methods=["POST"])
def buscar_por_nombre():
    try:
        data = request.get_json(silent=True) or {}

        texto = normalizar_texto(data.get("texto", ""))
        limit = data.get("limit", 50)

        try:
            limit = int(limit)
        except Exception:
            limit = 50

        if limit <= 0:
            limit = 50

        if texto == "":
            return jsonify({
                "ok": False,
                "mensaje": "Debes indicar un texto para buscar por nombre."
            }), 400

        df = cargar_bares()

        if df.empty:
            return jsonify({
                "ok": True,
                "mensaje": "No hay bares disponibles.",
                "recomendaciones": []
            }), 200

        df = enriquecer_bares_con_ciudad(df)

        if "placeID" in df.columns:
            df["placeID"] = pd.to_numeric(df["placeID"], errors="coerce")
            df = df.dropna(subset=["placeID"]).copy()
            df["placeID"] = df["placeID"].astype(int)

        if "nombre" not in df.columns:
            return jsonify({
                "ok": False,
                "mensaje": "El CSV de bares no contiene la columna 'nombre'."
            }), 500

        # Búsqueda parcial, sin distinguir mayúsculas/minúsculas
        patron = texto.lower().strip()

        df["nombre_norm"] = df["nombre"].fillna("").astype(str).str.strip()
        df_filtrado = df[
            df["nombre_norm"].str.lower().str.contains(patron, regex=False)
        ].copy()

        df_filtrado = df_filtrado.head(limit)

        recomendaciones = []
        for _, fila in df_filtrado.iterrows():
            recomendaciones.append({
                "placeID": int(fila["placeID"]),
                "nombre": normalizar_texto(fila.get("nombre", "")),
                "photo": normalizar_texto(fila.get("photo", "")),
                "types": normalizar_texto(fila.get("types", "")),
                "price_level": normalizar_texto(fila.get("price_level", "")),
                "val_media": obtener_valor_numerico(fila.get("val_media"), None),
                "descripcion": normalizar_texto(fila.get("descripcion", "")),
                "texto_semantico": normalizar_texto(fila.get("texto_semantico", "")),
                "opening_hours_weekday_text": normalizar_texto(fila.get("opening_hours_weekday_text", "")),
                "calle": normalizar_texto(fila.get("calle", "")),
                "zona": normalizar_texto(fila.get("ciudad", "")),
                "ciudad": normalizar_texto(fila.get("ciudad", ""))
            })

        return jsonify({
            "ok": True,
            "mensaje": f"Se han encontrado {len(recomendaciones)} bares por búsqueda de nombre.",
            "recomendaciones": recomendaciones
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "mensaje": f"Error buscando por nombre: {str(e)}"
        }), 500

if __name__ == "__main__":
    inicializar_recomendador()
    app.run(host="0.0.0.0", debug=False, port=5000)
else:
    inicializar_recomendador()