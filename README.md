# TFG-SR_RESTAURANTES — Sistema de Recomendación de Bares y Restaurantes en Jaén

Sistema de recomendación hiperlocal de bares y restaurantes para la provincia de Jaén que combina **filtrado colaborativo (BPR)**, **filtrado basado en contenido** y **búsqueda semántica** con una estrategia de switching híbrido que se adapta automáticamente al nivel de interacción de cada usuario.

## Tecnologías

| Capa | Stack |
|---|---|
| Backend | Python 3.11 · Flask · pandas · scikit-learn |
| Machine Learning | **cornac** (BPR) · **sentence-transformers** (`all-MiniLM-L6-v2`) |
| Frontend | HTML5 · CSS3 · Vanilla JavaScript · `localStorage` (no frameworks) |
| Almacenamiento | CSV + NumPy `.npy` (sin base de datos) |
| Contenedores | Docker + docker-compose, puerto **8000** |

## Arquitectura

```
tfg-adrian-murillo/
├── backend/
│   ├── app.py                    # Flask API + ruteo
│   └── recomender_refresh.py   # Actualización asíncrona de modelos en background
├── src/
│   ├── models/                   # Motor de recomendación
│   │   ├── collaborative_bpr.py      # BPR (Bayesian Personalized Ranking)
│   │   ├── content_based.py          # Content-Based con embeddings
│   │   ├── hybrid_switching.py       # Orquestador híbrido
│   │   ├── busqueda_semantica_bares.py # Búsqueda por texto natural
│   │   └── popularity.py                 # Baseline de popularidad
│   ├── preprocessing/
│   │   └── enriquecer_datos.py   # Enriquecimiento de datos desde CSVs → JSON
│   ├── evaluation/
│   │   ├── analisis_dataset.py
│   │   └── generar_embdings/
│   │       ├── crear_embedings_bares.py      # Genera los embedings de los bares
│   │       └── crear_embedings_usuarios.py          # Genera los embedings de los usuarios
│   └── experiments/
├── web/
│   ├── html/   (10 páginas)
│   ├── js/     (header, traduccion, inicio, resultados, bar, perfil, login, register)
│   └── css/
├── data/jaen/
│   ├── bares_finales.csv
│   ├── usuarios_finales.csv
│   ├── opiniones.csv
│   ├── favoritos.csv
│   ├── cp_jaen.csv
│   ├── json/ (bares_enriquecidos.json, usuarios_enriquecidos.json)
│   └── embeddings/ (.npy + .csv indices)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Motor de recomendación — Estrategia híbrida switching

El sistema elige qué modelo usar según el número de interacciones (`n_interacciones`) del usuario:

| Interacciones | Estrategia |
|---|---|
| 0 | Sin recomendaciones (cold start) |
| 1 – 4 | Content-Based (CB) exclusivamente |
| 5 – 6 | Híbrido 50% BPR + 50% CB |
| 7 – 14 | Híbrido 60% BPR + 40% CB |
| 15+ | Híbrido 70% BPR + 30% CB |

### Detalles de cada componente

**Content-Based:** calcula similitud coseno entre los embeddings de usuario y de bares (ambos en el mismo espacio vectorial). Los embeddings se generan a partir del texto enriquecido (nombre, tipos, descripción, precio, horarios y opiniones).

**Collaborative BPR:** usa el algoritmo BPR de cornac con factores `k=50`, `max_iter=100`, `learning_rate=0.01`, `lambda_reg=0.01`. Solo considera interacciones positivas (rating ≥ 4). Se re-entrena periódicamente en un hilo daemon con debounce de 15 s.

**Búsqueda semántica:** el usuario escribe una consulta libre (mínimo 20 palabras), se codifica con `all-MiniLM-L6-v2`, se calcula similitud coseno con todos los bares y se aplica **reranking** con reglas explícitas que detectan y premian/despremia restricciones: tipo de cocina, presupuesto, horarios, reservas.

**Refresco en vivo:** cada nueva opinión reconstruye inmediatamente el embedding del usuario y del bar, actualiza métricas y marca el BPR como "dirty" para re-entrenamiento diferido.

## API REST

### Autenticación
| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/login` | Username + password |
| `POST` | `/register` | Registro con validaciones |

### Recomendaciones
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/recomendaciones/<user_id>?limit=20` | Recomendaciones personales + metadatos de estrategia |

### Opiniones
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/opiniones/<place_id>` | Opiniones de un bar |
| `GET` | `/opiniones/usuario/<user_id>` | Opiniones de un usuario |
| `POST` | `/opiniones` | Crear opinión (rating 1-5) |

### Favoritos
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/favoritos/<user_id>` | Listado de favoritos |
| `POST` | `/favoritos` | Añadir favorito |
| `DELETE` | `/favoritos` | Eliminar favorito |

### Búsqueda y filtros
| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/busqueda-semantica` | Búsqueda por texto libre + reranking |
| `GET` | `/filtros/opciones` | Opciones disponibles (tipos, precios, zonas) |
| `POST` | `/buscar/filtros` | Búsqueda por filtros (ordenable por rating o precio) |
| `POST` | `/buscar/nombre` | Búsqueda difusa por nombre |

## Instalación

### Opción A — Docker (recomendada)

```bash
docker-compose up --build
```

Accede a `http://localhost:8000/web/html/inicio.html`.

### Opción B — Local

```bash
# Entorno virtual
python3 -m venv .venv && source .venv/bin/activate

# Dependencias
pip install -r requirements.txt

# Descargar el modelo de sentence-transformers
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Ejecutar
python backend/app.py
```

Accede a `http://localhost:5000/web/html/inicio.html`.

## Estructura de datos (CSVs en `data/jaen/`)

**`bares_finales.csv`** — `placeID`, `nombre`, `lat`, `lon`, `cod_postal`, `calle`, `val_media`, `num_val`, `price_level`, `website`, `opening_hours_weekday_text`, `types`, `texto_semantico`, `photo`, `descripcion`

**`usuarios_finales.csv`** — `user_id`, `username`, `preferencias`, `email`, `n_interacciones`, `top_types`, `avg_price_level_likes`, `password`, `fecha_nacimiento`

**`opiniones.csv`** — `placeID`, `user_id`, `rating`, `text`, `fecha_publicacion`

**`favoritos.csv`** — `user_id`, `placeID`

**`cp_jaen.csv`** — `postal_code`, `ciudad`, `provincia`, `pais`

## Frontend — Páginas

| Página | Archivo | Descripción |
|---|---|---|
| Inicio | `inicio.html` | Búsqueda por nombre/filtros/descripción + carruseles destacados |
| Login | `login.html` | Formulario con toggle de visibilidad de contraseña |
| Registro | `register.html` | Validación completa del formulario |
| Perfil | `perfil.html` | Datos del usuario, opiniones y favoritos |
| Resultados | `resultados.html` | Resultados con panel de filtros lateral |
| Detalle bar | `bar.html` | Info completa, reseñas y formulario de revisión |
| Contacto | `contacta.html` | Formulario + datos de contacto |
| Sobre la aplicación | `sobre-aplicacion.html` | Descripción del proyecto y funcionalidades |
| FAQ | `preguntas.html` | Preguntas frecuentes (acordeón) |
| Cabecera | `cabecera.html` | Componente reutilizable de navegación |

Características: **i18n** (es/en) con `data-i18n`, sesión con `localStorage`, diseño responsivo, cero frameworks.

## Evaluación

- Baseline de popularidad con evaluación leave-one-out: **Recall@K** y **NDCG@K** (`src/experiments/run_pop_jaen.py`)
- Análisis de dataset: densidad, coeficiente de Gini, distribución de ratings, sesgo de popularidad (`src/evaluation/analisis_dataset.py`)

## Notas de diseño

1. **Cold-start natural:** los usuarios nuevos sin interacciones no reciben recomendaciones; los que tienen 1-4 reciben contenido basado.
2. **Transición gradual:** la proporción colaborativo/contenido evoluciona de 0:1 a 7:3 con la interacción.
3. **Refresco en tiempo real:** cada opinión reconstruye embeddings al instante.
4. **BPR asíncrono:** re-entrenamiento en hilo daemon con debounce de 15 s.
5. **Cero dependencias externas en runtime:** sin APIs de Google, sin auth providers, sin bases de datos.
6. **Sin base de datos relacional:** persistencia en CSVs + embebidos `.npy`.

---

TFG de Adrian Murillo Moreno — Universidad de Jaén, 2025.
