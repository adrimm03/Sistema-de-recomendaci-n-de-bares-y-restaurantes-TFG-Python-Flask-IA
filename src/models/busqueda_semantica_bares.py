# ============================================================
# Nombre del alumno: Adrián Murillo Moreno
# Descripción: Búsqueda semántica de bares a partir de una frase
#              escrita por el usuario.
#
# Mejoras incluidas:
# - Búsqueda semántica con embeddings
# - Reordenación por reglas simples para cocina, precio, reservas y horario
# - Opción de salida corta por consola (solo placeID y nombre)
# ============================================================

import argparse
import json
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


DIAS_SEMANA = [
    "lunes", "martes", "miércoles", "miercoles", "jueves", "viernes", "sábado", "sabado", "domingo"
]

MAPA_COCINAS = {
    "italiana": ["italiana", "italiano", "pizza", "pizzer", "pasta", "lasaña", "lasaña", "carbonara", "bolognesa", "risotto", "trattoria"],
    "mexicana": ["mexicana", "mexicano", "taco", "tacos", "burrito", "quesadilla", "nachos", "guacamole"],
    "china": ["china", "chino", "arroz tres delicias", "rollito", "wok", "tallarines"],
    "japonesa": ["japonesa", "japones", "sushi", "ramen", "nigiri", "maki", "yakisoba"],
    "hamburguesas": ["hamburguesa", "hamburguesas", "burger"],
    "tapas": ["tapa", "tapas", "tapear", "tapeo"],
}

PALABRAS_RESERVA = ["reserva", "reservas", "reservar", "admite reservas"]
PALABRAS_ECONOMICO = ["económico", "economico", "barato", "barata", "buen precio", "precios bajos", "precio razonable"]


class BuscadorSemanticoBares:
    def __init__(
        self,
        bars_csv: str,
        opinions_csv: str,
        bar_embeddings_path: str,
        bar_index_path: str,
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.bars_csv = bars_csv
        self.opinions_csv = opinions_csv
        self.bar_embeddings_path = bar_embeddings_path
        self.bar_index_path = bar_index_path
        self.model_name = model_name

        self.df_bars: Optional[pd.DataFrame] = None
        self.df_opinions: Optional[pd.DataFrame] = None
        self.bar_embeddings: Optional[np.ndarray] = None
        self.bar_index: Optional[pd.DataFrame] = None
        self.item2row: Dict[int, int] = {}
        self.row2item: Dict[int, int] = {}
        self.model: Optional[SentenceTransformer] = None

        self._cargar_datos()

    def _esta_vacio(self, valor: Any) -> bool:
        if pd.isna(valor):
            return True
        return str(valor).strip() == ""

    def _limpiar_texto(self, texto: Any) -> str:
        if self._esta_vacio(texto):
            return ""
        texto = str(texto).strip().lower()
        texto = texto.replace("|", " ")
        texto = texto.replace("\n", " ")
        texto = texto.replace("\r", " ")
        texto = re.sub(r"\s+", " ", texto).strip()
        return texto

    def _normalizar_types(self, types_text: Any) -> str:
        if self._esta_vacio(types_text):
            return ""
        return self._limpiar_texto(str(types_text).replace("|", ", "))

    def _valor_json(self, valor: Any) -> Any:
        if pd.isna(valor):
            return None
        if isinstance(valor, np.integer):
            return int(valor)
        if isinstance(valor, np.floating):
            valor_float = float(valor)
            return int(valor_float) if valor_float.is_integer() else valor_float
        return valor

    def _parsear_horario(self, horario: Any) -> List[str]:
        if self._esta_vacio(horario):
            return []
        return [p.strip() for p in str(horario).split("|") if p.strip()]

    def _cargar_datos(self) -> None:
        self.df_bars = pd.read_csv(self.bars_csv)
        self.df_opinions = pd.read_csv(self.opinions_csv)
        self.bar_embeddings = np.load(self.bar_embeddings_path)
        self.bar_index = pd.read_csv(self.bar_index_path)

        if "placeID" not in self.df_bars.columns:
            raise ValueError("El CSV de bares debe contener la columna 'placeID'.")
        if "placeID" not in self.df_opinions.columns:
            raise ValueError("El CSV de opiniones debe contener al menos la columna 'placeID'.")
        if not {"placeID", "row_idx"}.issubset(self.bar_index.columns):
            raise ValueError("El índice de embeddings debe contener 'placeID' y 'row_idx'.")

        self.df_bars["placeID"] = pd.to_numeric(self.df_bars["placeID"], errors="coerce")
        self.df_opinions["placeID"] = pd.to_numeric(self.df_opinions["placeID"], errors="coerce")
        self.bar_index["placeID"] = pd.to_numeric(self.bar_index["placeID"], errors="coerce")
        self.bar_index["row_idx"] = pd.to_numeric(self.bar_index["row_idx"], errors="coerce")

        self.df_bars = self.df_bars.dropna(subset=["placeID"]).copy()
        self.df_opinions = self.df_opinions.dropna(subset=["placeID"]).copy()
        self.bar_index = self.bar_index.dropna(subset=["placeID", "row_idx"]).copy()

        self.df_bars["placeID"] = self.df_bars["placeID"].astype(int)
        self.df_opinions["placeID"] = self.df_opinions["placeID"].astype(int)
        self.bar_index["placeID"] = self.bar_index["placeID"].astype(int)
        self.bar_index["row_idx"] = self.bar_index["row_idx"].astype(int)

        self.bar_index = self.bar_index[
            (self.bar_index["row_idx"] >= 0) & (self.bar_index["row_idx"] < len(self.bar_embeddings))
        ].copy()

        self.item2row = dict(zip(self.bar_index["placeID"], self.bar_index["row_idx"]))
        self.row2item = dict(zip(self.bar_index["row_idx"], self.bar_index["placeID"]))
        self.model = SentenceTransformer(self.model_name)

    def _cosine_scores_dense(self, query_vec: np.ndarray, item_matrix: np.ndarray, eps: float = 1e-12) -> np.ndarray:
        qv = np.asarray(query_vec, dtype=float)
        im = np.asarray(item_matrix, dtype=float)
        qv = qv / (np.linalg.norm(qv) + eps)
        im = im / (np.linalg.norm(im, axis=1, keepdims=True) + eps)
        return im @ qv

    def _detectar_cocina(self, consulta: str) -> Optional[str]:
        consulta = self._limpiar_texto(consulta)
        for cocina, palabras in MAPA_COCINAS.items():
            if any(p in consulta for p in palabras):
                return cocina
        return None

    def _detectar_dia_hora(self, consulta: str) -> Tuple[Optional[str], Optional[int]]:
        texto = self._limpiar_texto(consulta)

        dia_detectado = None
        for dia in DIAS_SEMANA:
            if dia in texto:
                dia_detectado = dia
                break

        hora_min = None

        m = re.search(r"(\d{1,2})[:h](\d{2})", texto)
        if m:
            hora = int(m.group(1))
            minuto = int(m.group(2))
            hora_min = hora * 60 + minuto
        elif "cuatro y media" in texto:
            hora_min = 16 * 60 + 30
        elif "cinco y media" in texto:
            hora_min = 17 * 60 + 30
        elif "seis y media" in texto:
            hora_min = 18 * 60 + 30

        return dia_detectado, hora_min

    def _rango_precio_economico(self, price_level: Any) -> bool:
        if self._esta_vacio(price_level):
            return False
        texto = self._limpiar_texto(price_level)
        return "1-10" in texto or "10€" in texto or "barato" in texto or "econ" in texto

    def _texto_bar_completo(self, fila: pd.Series) -> str:
        partes = []
        for col in ["nombre", "types", "texto_semantico", "descripcion", "price_level", "opening_hours_weekday_text"]:
            if col in fila.index and not self._esta_vacio(fila[col]):
                partes.append(str(fila[col]))
        return self._limpiar_texto(" ".join(partes))

    def _bar_admite_reservas(self, fila: pd.Series) -> bool:
        return "admite reservas" in self._texto_bar_completo(fila)

    def _bar_tiene_cocina(self, fila: pd.Series, cocina: Optional[str]) -> bool:
        if cocina is None:
            return True
        texto = self._texto_bar_completo(fila)
        palabras = MAPA_COCINAS.get(cocina, [])
        return any(p in texto for p in palabras)

    def _a_minutos(self, hhmm: str) -> Optional[int]:
        m = re.match(r"\s*(\d{1,2}):(\d{2})\s*$", hhmm)
        if not m:
            return None
        return int(m.group(1)) * 60 + int(m.group(2))

    def _bar_abierto_en(self, fila: pd.Series, dia: Optional[str], hora_min: Optional[int]) -> Optional[bool]:
        if dia is None or hora_min is None:
            return None
        horario = fila.get("opening_hours_weekday_text", None)
        if self._esta_vacio(horario):
            return None

        entradas = self._parsear_horario(horario)
        dia_base = dia.replace("é", "e").replace("á", "a")
        for entrada in entradas:
            entrada_l = self._limpiar_texto(entrada)
            entrada_dia = entrada_l.split(":", 1)[0].strip()
            entrada_dia_base = entrada_dia.replace("é", "e").replace("á", "a")
            if entrada_dia_base != dia_base:
                continue
            if "cerrado" in entrada_l:
                return False
            if ":" not in entrada_l:
                return None
            tramo = entrada_l.split(":", 1)[1].strip()
            partes = [p.strip() for p in tramo.split("–")]
            if len(partes) != 2:
                partes = [p.strip() for p in tramo.split("-")]
            if len(partes) != 2:
                return None
            inicio = self._a_minutos(partes[0])
            fin = self._a_minutos(partes[1])
            if inicio is None or fin is None:
                return None
            if fin == 24 * 60:
                fin = 24 * 60
            return inicio <= hora_min <= fin
        return None

    def _obtener_opiniones_bar(self, place_id: int, max_opiniones: int = 5) -> List[Dict[str, Any]]:
        df = self.df_opinions[self.df_opinions["placeID"] == place_id].copy()
        if df.empty:
            return []

        if "text" in df.columns:
            df["text"] = df["text"].fillna("").astype(str)
            df["texto_limpio"] = df["text"].apply(self._limpiar_texto)
        else:
            df["text"] = ""
            df["texto_limpio"] = ""

        if "rating" in df.columns:
            df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
        else:
            df["rating"] = np.nan

        df["len_texto"] = df["texto_limpio"].str.len()
        df = df.sort_values(by=["rating", "len_texto"], ascending=[False, False], na_position="last")

        resultados: List[Dict[str, Any]] = []
        for _, fila in df.head(max_opiniones).iterrows():
            opinion = {}
            for col in df.columns:
                if col in {"texto_limpio", "len_texto"}:
                    continue
                opinion[col] = self._valor_json(fila[col])
            resultados.append(opinion)
        return resultados

    def _obtener_detalles_bar(self, place_id: int, score: float, max_opiniones: int = 5) -> Dict[str, Any]:
        fila_df = self.df_bars[self.df_bars["placeID"] == place_id]
        if fila_df.empty:
            return {"placeID": place_id, "score_semantico": float(score), "opiniones": self._obtener_opiniones_bar(place_id, max_opiniones=max_opiniones)}

        fila = fila_df.iloc[0]
        detalles: Dict[str, Any] = {}
        for col in self.df_bars.columns:
            detalles[col] = self._valor_json(fila[col])
        detalles["score_semantico"] = float(score)
        detalles["types_legible"] = self._normalizar_types(fila.get("types", ""))
        detalles["opening_hours_parseado"] = self._parsear_horario(fila.get("opening_hours_weekday_text", ""))
        detalles["opiniones"] = self._obtener_opiniones_bar(place_id, max_opiniones=max_opiniones)
        return detalles

    def buscar(self, frase_usuario: str, top_k: int = 10, max_opiniones: int = 5) -> Dict[str, Any]:
        frase_limpia = self._limpiar_texto(frase_usuario)
        if frase_limpia == "":
            raise ValueError("La frase de búsqueda no puede estar vacía.")

        cocina = self._detectar_cocina(frase_limpia)
        dia, hora_min = self._detectar_dia_hora(frase_limpia)
        pide_reservas = any(p in frase_limpia for p in PALABRAS_RESERVA)
        pide_economico = any(p in frase_limpia for p in PALABRAS_ECONOMICO)

        query_vec = self.model.encode(frase_limpia)
        scores_sem = self._cosine_scores_dense(query_vec, self.bar_embeddings)
        ranked_idx = np.argsort(scores_sem)[::-1]

        candidatos: List[Tuple[float, int, float]] = []

        for row_idx in ranked_idx:
            place_id = self.row2item.get(int(row_idx))
            if place_id is None:
                continue

            fila_df = self.df_bars[self.df_bars["placeID"] == place_id]
            if fila_df.empty:
                continue
            fila = fila_df.iloc[0]

            score_final = float(scores_sem[row_idx])

            # Cocina como restricción fuerte si se detecta en la consulta
            if cocina is not None:
                if self._bar_tiene_cocina(fila, cocina):
                    score_final += 0.20
                else:
                    score_final -= 0.35

            # Precio económico
            if pide_economico:
                if self._rango_precio_economico(fila.get("price_level", None)):
                    score_final += 0.08
                else:
                    score_final -= 0.08

            # Reservas
            if pide_reservas:
                if self._bar_admite_reservas(fila):
                    score_final += 0.08
                else:
                    score_final -= 0.08

            # Horario
            abierto = self._bar_abierto_en(fila, dia, hora_min)
            if abierto is True:
                score_final += 0.15
            elif abierto is False:
                score_final -= 0.25

            candidatos.append((score_final, place_id, float(scores_sem[row_idx])))

        candidatos.sort(key=lambda x: x[0], reverse=True)
        candidatos = candidatos[:top_k]

        resultados: List[Dict[str, Any]] = []
        for score_final, place_id, score_sem in candidatos:
            detalles = self._obtener_detalles_bar(place_id=place_id, score=score_sem, max_opiniones=max_opiniones)
            detalles["score_rerank"] = float(score_final)
            resultados.append(detalles)

        return {
            "consulta_usuario": frase_limpia,
            "modelo_embedding": self.model_name,
            "total_resultados": len(resultados),
            "restricciones_detectadas": {
                "cocina": cocina,
                "dia": dia,
                "hora_minutos": hora_min,
                "economico": pide_economico,
                "reservas": pide_reservas,
            },
            "resultados": resultados,
        }

    def imprimir_resumen(self, busqueda: Dict[str, Any], modo_corto: bool = False) -> None:
        print("=" * 80)
        print(f"Consulta: {busqueda['consulta_usuario']}")
        print(f"Modelo de embeddings: {busqueda['modelo_embedding']}")
        print(f"Número de resultados: {busqueda['total_resultados']}")
        print("=" * 80)

        if modo_corto:
            for i, bar in enumerate(busqueda["resultados"], start=1):
                print(f"[{i}] placeID={bar.get('placeID')} | nombre={bar.get('nombre', 'Sin nombre')}")
            return

        for i, bar in enumerate(busqueda["resultados"], start=1):
            print(f"\n[{i}] {bar.get('nombre', 'Sin nombre')} (placeID={bar.get('placeID')})")
            print(f"Score semántico: {bar.get('score_semantico'):.4f}")
            print(f"Score final rerank: {bar.get('score_rerank'):.4f}")
            print(f"Tipo: {bar.get('types_legible', '')}")
            print(f"Dirección: {bar.get('calle', '')}")
            print(f"Precio: {bar.get('price_level', '')}")
            print(f"Valoración media: {bar.get('val_media', '')}")
            print(f"Número de valoraciones: {bar.get('num_val', '')}")
            print("Horario:")
            horarios = bar.get("opening_hours_parseado", [])
            if horarios:
                for h in horarios:
                    print(f"  - {h}")
            else:
                print("  - No disponible")

            print("Opiniones destacadas:")
            opiniones = bar.get("opiniones", [])
            if opiniones:
                for op in opiniones:
                    rating = op.get("rating", "")
                    texto = str(op.get("text", "")).strip()
                    if texto == "":
                        texto = "Sin comentario"
                    print(f"  - Rating {rating}: {texto}")
            else:
                print("  - No hay opiniones disponibles")

            print("Detalles completos del bar:")
            detalles_copia = {k: v for k, v in bar.items() if k != "opiniones"}
            print(json.dumps(detalles_copia, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Busca bares similares a una frase escrita por el usuario usando embeddings semánticos.")
    parser.add_argument("--consulta", type=str, required=True, help="Frase escrita por el usuario")
    parser.add_argument("--top_k", type=int, default=10, help="Número de bares a devolver")
    parser.add_argument("--max_opiniones", type=int, default=5, help="Número máximo de opiniones por bar")
    parser.add_argument("--modo_corto", action="store_true", help="Muestra solo placeID y nombre por consola")
    parser.add_argument("--bars_csv", type=str, default="data/jaen/bares_finales.csv", help="Ruta al CSV de bares")
    parser.add_argument("--opinions_csv", type=str, default="data/jaen/opiniones.csv", help="Ruta al CSV de opiniones")
    parser.add_argument("--bar_embeddings_path", type=str, default="data/jaen/embeddings/embeddings_bares.npy", help="Ruta al .npy con embeddings de bares")
    parser.add_argument("--bar_index_path", type=str, default="data/jaen/embeddings/embeddings_index.csv", help="Ruta al CSV placeID -> row_idx")
    parser.add_argument("--output_json", type=str, default="", help="Si se indica, guarda también la salida completa en JSON")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    buscador = BuscadorSemanticoBares(
        bars_csv=args.bars_csv,
        opinions_csv=args.opinions_csv,
        bar_embeddings_path=args.bar_embeddings_path,
        bar_index_path=args.bar_index_path,
    )

    resultado = buscador.buscar(
        frase_usuario=args.consulta,
        top_k=args.top_k,
        max_opiniones=args.max_opiniones,
    )

    buscador.imprimir_resumen(resultado, modo_corto=args.modo_corto)

    if args.output_json.strip() != "":
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
        print("\nSalida JSON guardada en:", args.output_json)


if __name__ == "__main__":
    main()
