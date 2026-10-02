#!/usr/bin/env python3
# ============================================================
# Nombre del alumno: Adrián Murillo Moreno
# Descripción breve del ejercicio:
# Analiza la calidad del dataset de recomendación de bares.
# Calcula distribución de opiniones por bar y por usuario,
# sparsity, cobertura, sesgo de popularidad y métricas útiles
# para valorar si el CSV es adecuado para un sistema de
# recomendación colaborativo, basado en contenido e híbrido.
# ============================================================

import argparse
from pathlib import Path
import pandas as pd


def leer_csv_seguro(ruta_csv):
    ruta = Path(ruta_csv)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el archivo: {ruta}")
    return pd.read_csv(ruta)


def normalizar_opiniones(df):
    columnas_necesarias = {"placeID", "user_id", "rating"}
    faltan = columnas_necesarias - set(df.columns)

    if faltan:
        raise ValueError(
            f"El CSV de opiniones debe contener {sorted(columnas_necesarias)}. "
            f"Faltan: {sorted(faltan)}"
        )

    df = df.copy()
    df["placeID"] = pd.to_numeric(df["placeID"], errors="coerce")
    df["user_id"] = pd.to_numeric(df["user_id"], errors="coerce")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df.dropna(subset=["placeID", "user_id", "rating"]).copy()
    df["placeID"] = df["placeID"].astype(int)
    df["user_id"] = df["user_id"].astype(int)
    df["rating"] = df["rating"].astype(float)
    return df


def normalizar_bares(df):
    if "placeID" not in df.columns:
        raise ValueError("El CSV de bares debe contener la columna 'placeID'.")
    df = df.copy()
    df["placeID"] = pd.to_numeric(df["placeID"], errors="coerce")
    df = df.dropna(subset=["placeID"]).copy()
    df["placeID"] = df["placeID"].astype(int)
    return df


def distribucion_frecuencias(serie_conteos):
    dist = serie_conteos.value_counts().sort_index()
    return pd.DataFrame({
        "n_interacciones": dist.index.astype(int),
        "n_elementos": dist.values.astype(int)
    })


def top_n(serie, n=10):
    top = serie.sort_values(ascending=False).head(n)
    return [(int(idx), int(val)) for idx, val in top.items()]


def porcentaje(valor, total):
    if total == 0:
        return 0.0
    return (valor / total) * 100.0


def gini_aprox(valores):
    valores = [float(v) for v in valores if v is not None]
    valores = [v for v in valores if v >= 0]

    if len(valores) == 0:
        return 0.0

    valores.sort()
    n = len(valores)
    suma = sum(valores)

    if suma == 0:
        return 0.0

    acumulado = 0.0
    for i, x in enumerate(valores, start=1):
        acumulado += i * x

    return (2 * acumulado) / (n * suma) - (n + 1) / n


def clasificar_densidad(sparsity_pct):
    if sparsity_pct >= 99.5:
        return "Muy disperso"
    if sparsity_pct >= 98.0:
        return "Disperso"
    if sparsity_pct >= 95.0:
        return "Moderadamente disperso"
    return "Aceptable"


def interpretar_dataset(metricas):
    conclusiones = []

    sparsity = metricas["sparsity_pct"]
    media_user = metricas["media_opiniones_por_usuario"]
    media_bar = metricas["media_opiniones_por_bar"]
    pct_bares_1 = metricas["pct_bares_con_1_opinion"]
    pct_users_1 = metricas["pct_usuarios_con_1_opinion"]

    if sparsity >= 99.5:
        conclusiones.append(
            "La matriz usuario-item es muy dispersa. El filtrado colaborativo puro puede sufrir bastante."
        )
    elif sparsity >= 98.0:
        conclusiones.append(
            "La matriz usuario-item es dispersa. El colaborativo puede funcionar, pero conviene reforzarlo con contenido o enfoque híbrido."
        )
    else:
        conclusiones.append(
            "La dispersión no es extrema para este dominio, lo que favorece algo más al componente colaborativo."
        )

    if media_user < 3:
        conclusiones.append(
            "La media de opiniones por usuario es baja. Habrá bastantes usuarios fríos o con poco historial."
        )
    elif media_user < 6:
        conclusiones.append(
            "La media de opiniones por usuario es moderada. El híbrido debería rendir mejor que un colaborativo puro."
        )
    else:
        conclusiones.append(
            "La media de opiniones por usuario es razonable para explotar patrones colaborativos."
        )

    if media_bar < 3:
        conclusiones.append(
            "Muchos bares tienen pocas opiniones. Esto limita la señal colaborativa a nivel de ítem."
        )
    elif media_bar < 6:
        conclusiones.append(
            "Los bares tienen una cobertura media moderada. El contenido sigue siendo importante."
        )
    else:
        conclusiones.append(
            "La cobertura media por bar es buena para apoyar ranking y popularidad."
        )

    if pct_bares_1 > 40:
        conclusiones.append(
            "Hay un sesgo notable hacia bares con una sola opinión. Puede haber mucho ruido y poca robustez por ítem."
        )

    if pct_users_1 > 40:
        conclusiones.append(
            "Hay muchos usuarios con una sola opinión. El cold-start de usuario será un problema importante."
        )

    conclusiones.append(
        "Para tu sistema concreto, un enfoque híbrido como el que ya tienes suele ser más apropiado que depender solo del filtrado colaborativo."
    )

    return conclusiones


def analizar_dataset(opiniones_csv, bares_csv=None, salida_dir=None):
    df_op = leer_csv_seguro(opiniones_csv)
    df_op = normalizar_opiniones(df_op)

    total_filas_originales = len(df_op)
    duplicados_usuario_item = int(df_op.duplicated(subset=["user_id", "placeID"]).sum())
    df_unique = df_op.drop_duplicates(subset=["user_id", "placeID"]).copy()

    df_bares = None
    total_bares_catalogo = None
    if bares_csv:
        df_bares = leer_csv_seguro(bares_csv)
        df_bares = normalizar_bares(df_bares)
        total_bares_catalogo = int(df_bares["placeID"].nunique())

    total_interacciones = int(len(df_unique))
    total_usuarios = int(df_unique["user_id"].nunique())
    total_bares_con_opinion = int(df_unique["placeID"].nunique())

    opiniones_por_bar = df_unique.groupby("placeID").size()
    opiniones_por_usuario = df_unique.groupby("user_id").size()

    dist_bares = distribucion_frecuencias(opiniones_por_bar)
    dist_usuarios = distribucion_frecuencias(opiniones_por_usuario)

    media_op_bar = float(opiniones_por_bar.mean()) if len(opiniones_por_bar) > 0 else 0.0
    mediana_op_bar = float(opiniones_por_bar.median()) if len(opiniones_por_bar) > 0 else 0.0
    max_op_bar = int(opiniones_por_bar.max()) if len(opiniones_por_bar) > 0 else 0

    media_op_user = float(opiniones_por_usuario.mean()) if len(opiniones_por_usuario) > 0 else 0.0
    mediana_op_user = float(opiniones_por_usuario.median()) if len(opiniones_por_usuario) > 0 else 0.0
    max_op_user = int(opiniones_por_usuario.max()) if len(opiniones_por_usuario) > 0 else 0

    bares_1 = int((opiniones_por_bar == 1).sum())
    usuarios_1 = int((opiniones_por_usuario == 1).sum())

    pct_bares_1 = porcentaje(bares_1, total_bares_con_opinion)
    pct_users_1 = porcentaje(usuarios_1, total_usuarios)

    if total_bares_catalogo is None:
        total_bares_para_matriz = total_bares_con_opinion
    else:
        total_bares_para_matriz = total_bares_catalogo

    celdas_totales = total_usuarios * total_bares_para_matriz
    densidad = (total_interacciones / celdas_totales) if celdas_totales > 0 else 0.0
    sparsity = 1.0 - densidad
    sparsity_pct = sparsity * 100.0
    densidad_pct = densidad * 100.0

    rating_mean = float(df_unique["rating"].mean()) if len(df_unique) > 0 else 0.0
    rating_std = float(df_unique["rating"].std()) if len(df_unique) > 1 else 0.0
    dist_ratings = (
        df_unique["rating"].round(2).value_counts().sort_index().reset_index()
    )
    dist_ratings.columns = ["rating", "n_opiniones"]

    top_bares = top_n(opiniones_por_bar, n=10)
    top_usuarios = top_n(opiniones_por_usuario, n=10)

    gini_bares = float(gini_aprox(opiniones_por_bar.tolist()))
    gini_usuarios = float(gini_aprox(opiniones_por_usuario.tolist()))

    cobertura_catalogo_pct = None
    bares_sin_opinion = None
    if total_bares_catalogo is not None and total_bares_catalogo > 0:
        cobertura_catalogo_pct = porcentaje(total_bares_con_opinion, total_bares_catalogo)
        bares_sin_opinion = int(total_bares_catalogo - total_bares_con_opinion)

    metricas = {
        "total_filas_csv_opiniones": total_filas_originales,
        "duplicados_usuario_item": duplicados_usuario_item,
        "total_interacciones_unicas": total_interacciones,
        "total_usuarios_con_opiniones": total_usuarios,
        "total_bares_con_opiniones": total_bares_con_opinion,
        "total_bares_catalogo": total_bares_catalogo,
        "bares_sin_opinion": bares_sin_opinion,
        "cobertura_catalogo_pct": cobertura_catalogo_pct,
        "media_opiniones_por_bar": media_op_bar,
        "mediana_opiniones_por_bar": mediana_op_bar,
        "max_opiniones_en_un_bar": max_op_bar,
        "media_opiniones_por_usuario": media_op_user,
        "mediana_opiniones_por_usuario": mediana_op_user,
        "max_opiniones_de_un_usuario": max_op_user,
        "bares_con_1_opinion": bares_1,
        "usuarios_con_1_opinion": usuarios_1,
        "pct_bares_con_1_opinion": pct_bares_1,
        "pct_usuarios_con_1_opinion": pct_users_1,
        "densidad_pct": densidad_pct,
        "sparsity_pct": sparsity_pct,
        "clasificacion_sparsity": clasificar_densidad(sparsity_pct),
        "rating_medio": rating_mean,
        "rating_std": rating_std,
        "gini_popularidad_bares": gini_bares,
        "gini_actividad_usuarios": gini_usuarios
    }

    conclusiones = interpretar_dataset(metricas)

    print("=" * 80)
    print("ANÁLISIS DEL DATASET DE RECOMENDACIÓN")
    print("=" * 80)
    print(f"CSV opiniones: {opiniones_csv}")
    if bares_csv:
        print(f"CSV bares:     {bares_csv}")
    print("-" * 80)
    print(f"Filas originales en opiniones:               {metricas['total_filas_csv_opiniones']}")
    print(f"Duplicados usuario-item detectados:         {metricas['duplicados_usuario_item']}")
    print(f"Interacciones únicas usuario-item:          {metricas['total_interacciones_unicas']}")
    print(f"Usuarios con opiniones:                     {metricas['total_usuarios_con_opiniones']}")
    print(f"Bares con al menos una opinión:             {metricas['total_bares_con_opiniones']}")

    if metricas["total_bares_catalogo"] is not None:
        print(f"Bares totales en catálogo:                  {metricas['total_bares_catalogo']}")
        print(f"Bares sin opiniones:                        {metricas['bares_sin_opinion']}")
        print(f"Cobertura del catálogo con opiniones:       {metricas['cobertura_catalogo_pct']:.2f}%")

    print("-" * 80)
    print(f"Media opiniones por bar:                    {metricas['media_opiniones_por_bar']:.2f}")
    print(f"Mediana opiniones por bar:                  {metricas['mediana_opiniones_por_bar']:.2f}")
    print(f"Máx. opiniones en un bar:                   {metricas['max_opiniones_en_un_bar']}")
    print(f"Bares con una sola opinión:                 {metricas['bares_con_1_opinion']} ({metricas['pct_bares_con_1_opinion']:.2f}%)")
    print("-" * 80)
    print(f"Media opiniones por usuario:                {metricas['media_opiniones_por_usuario']:.2f}")
    print(f"Mediana opiniones por usuario:              {metricas['mediana_opiniones_por_usuario']:.2f}")
    print(f"Máx. opiniones de un usuario:               {metricas['max_opiniones_de_un_usuario']}")
    print(f"Usuarios con una sola opinión:              {metricas['usuarios_con_1_opinion']} ({metricas['pct_usuarios_con_1_opinion']:.2f}%)")
    print("-" * 80)
    print(f"Densidad matriz usuario-item:               {metricas['densidad_pct']:.4f}%")
    print(f"Sparsity matriz usuario-item:               {metricas['sparsity_pct']:.4f}%")
    print(f"Clasificación de sparsity:                  {metricas['clasificacion_sparsity']}")
    print("-" * 80)
    print(f"Rating medio:                               {metricas['rating_medio']:.4f}")
    print(f"Desviación típica rating:                   {metricas['rating_std']:.4f}")
    print(f"Gini popularidad de bares:                  {metricas['gini_popularidad_bares']:.4f}")
    print(f"Gini actividad de usuarios:                 {metricas['gini_actividad_usuarios']:.4f}")
    print("-" * 80)
    print("TOP 10 BARES CON MÁS OPINIONES")
    for place_id, n in top_bares:
        print(f"  - placeID {place_id}: {n} opiniones")
    print("-" * 80)
    print("TOP 10 USUARIOS CON MÁS OPINIONES")
    for user_id, n in top_usuarios:
        print(f"  - user_id {user_id}: {n} opiniones")
    print("-" * 80)
    print("DISTRIBUCIÓN DE OPINIONES POR BAR")
    for _, fila in dist_bares.iterrows():
        print(f"  - {int(fila['n_interacciones'])} opiniones -> {int(fila['n_elementos'])} bares")
    print("-" * 80)
    print("DISTRIBUCIÓN DE OPINIONES POR USUARIO")
    for _, fila in dist_usuarios.iterrows():
        print(f"  - {int(fila['n_interacciones'])} opiniones -> {int(fila['n_elementos'])} usuarios")
    print("-" * 80)
    print("DISTRIBUCIÓN DE RATINGS")
    for _, fila in dist_ratings.iterrows():
        print(f"  - rating {fila['rating']}: {int(fila['n_opiniones'])} opiniones")
    print("-" * 80)
    print("CONCLUSIONES AUTOMÁTICAS")
    for i, c in enumerate(conclusiones, start=1):
        print(f"  {i}. {c}")
    print("=" * 80)

    if salida_dir:
        salida = Path(salida_dir)
        salida.mkdir(parents=True, exist_ok=True)

        dist_bares.to_csv(salida / "distribucion_opiniones_por_bar.csv", index=False)
        dist_usuarios.to_csv(salida / "distribucion_opiniones_por_usuario.csv", index=False)
        dist_ratings.to_csv(salida / "distribucion_ratings.csv", index=False)

        metricas_df = pd.DataFrame([{"metrica": k, "valor": v} for k, v in metricas.items()])
        metricas_df.to_csv(salida / "metricas_dataset.csv", index=False)

        conclusiones_df = pd.DataFrame({
            "n": list(range(1, len(conclusiones) + 1)),
            "conclusion": conclusiones
        })
        conclusiones_df.to_csv(salida / "conclusiones_dataset.csv", index=False)

        top_bares_df = pd.DataFrame(top_bares, columns=["placeID", "n_opiniones"])
        top_bares_df.to_csv(salida / "top_bares_mas_opiniones.csv", index=False)

        top_usuarios_df = pd.DataFrame(top_usuarios, columns=["user_id", "n_opiniones"])
        top_usuarios_df.to_csv(salida / "top_usuarios_mas_opiniones.csv", index=False)

        print(f"Archivos de análisis guardados en: {salida.resolve()}")


def main():
    parser = argparse.ArgumentParser(
        description="Analiza un dataset de opiniones para valorar si es adecuado para recomendación."
    )

    parser.add_argument("--opiniones_csv", type=str, required=True, help="Ruta al CSV de opiniones.")
    parser.add_argument("--bares_csv", type=str, default="", help="Ruta al CSV de bares (opcional).")
    parser.add_argument("--salida_dir", type=str, default="", help="Directorio opcional para guardar CSVs.")

    args = parser.parse_args()

    analizar_dataset(
        opiniones_csv=args.opiniones_csv,
        bares_csv=args.bares_csv if args.bares_csv.strip() != "" else None,
        salida_dir=args.salida_dir if args.salida_dir.strip() != "" else None
    )


if __name__ == "__main__":
    main()
