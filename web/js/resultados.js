var BACKEND_URL = window.BACKEND_URL || "";

const menuToggle = document.getElementById("menuToggle");
const hamburgerDropdown = document.getElementById("hamburgerDropdown");
const profileToggle = document.getElementById("profileToggle");
const profileDropdown = document.getElementById("profileDropdown");

const resultadosGrid = document.getElementById("resultadosGrid");
const resultadosCount = document.getElementById("resultadosCount");
const resultadosMessage = document.getElementById("resultadosMessage");

const TIPOS_FIJOS = [
  { value: "", label: "Todos" },
  { value: "bar", label: "Bar" },
  { value: "bar de tapas", label: "Bar de tapas" },
  { value: "bar restaurante", label: "Bar restaurante" },
  { value: "cafe", label: "Café" },
  { value: "cerveceria", label: "Cervecería" },
  { value: "pub", label: "Pub" },
  { value: "restaurant", label: "Restaurante" },
  { value: "taberna", label: "Taberna" }
];

const PRECIOS_FIJOS = [
  { value: "", label: "Todos" },
  { value: "0€", label: "0€" },
  { value: "1-10€", label: "1-10€" },
  { value: "10-20€", label: "10-20€" },
  { value: "20-30€", label: "20-30€" },
  { value: "Más de 30€", label: "Más de 30€" }
];

// =========================
// SESIÓN
// =========================
function obtenerUsuarioLogueado() {
  const usuario = localStorage.getItem("usuarioLogueado");
  return usuario ? JSON.parse(usuario) : null;
}

function obtenerUsuarioValido() {
  const usuario = obtenerUsuarioLogueado();
  if (!usuario || !usuario.user_id) return null;
  return usuario;
}

// =========================
// URL / PARÁMETROS
// =========================
function obtenerParametroURL(nombre) {
  const params = new URLSearchParams(window.location.search);
  return params.get(nombre);
}

function contarPalabras(texto) {
  const limpio = (texto || "").trim();
  if (limpio === "") return 0;
  return limpio.split(/\s+/).length;
}

// =========================
// FAVORITOS
// =========================
function obtenerFavoritos() {
  const favoritos = localStorage.getItem("favoritos");
  return favoritos ? JSON.parse(favoritos) : [];
}

function guardarFavoritos(favoritos) {
  localStorage.setItem("favoritos", JSON.stringify(favoritos));
}

function esFavorito(placeID) {
  const favoritos = obtenerFavoritos();
  return favoritos.includes(Number(placeID));
}

async function sincronizarFavoritosDesdeBackend(userId) {
  try {
    const response = await fetch(`${BACKEND_URL}/favoritos/${userId}`);
    const data = await response.json();

    if (data.ok && Array.isArray(data.favoritos)) {
      guardarFavoritos(data.favoritos.map(Number));
    }
  } catch (error) {
    console.error("Error sincronizando favoritos:", error);
  }
}

async function toggleFavoritoBackend(userId, placeID, activar) {
  try {
    const response = await fetch(`${BACKEND_URL}/favoritos`, {
      method: activar ? "POST" : "DELETE",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        user_id: Number(userId),
        placeID: Number(placeID)
      })
    });

    const data = await response.json();
    return data.ok === true;
  } catch (error) {
    console.error("Error actualizando favorito en backend:", error);
    return false;
  }
}

// =========================
// MENÚS
// =========================
function inicializarMenus() {
  if (menuToggle && hamburgerDropdown && profileToggle && profileDropdown) {
    menuToggle.addEventListener("click", function (event) {
      event.stopPropagation();
      hamburgerDropdown.classList.toggle("show");
      profileDropdown.classList.remove("show");
    });

    profileToggle.addEventListener("click", function (event) {
      event.stopPropagation();
      profileDropdown.classList.toggle("show");
      hamburgerDropdown.classList.remove("show");
    });

    document.addEventListener("click", function () {
      hamburgerDropdown.classList.remove("show");
      profileDropdown.classList.remove("show");
    });
  }
}

// =========================
// TABS
// =========================
function inicializarTabs() {
  const modeButtons = document.querySelectorAll(".search-mode-btn");
  const modePanels = document.querySelectorAll(".search-mode-panel");

  modeButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const targetId = this.dataset.target;

      modeButtons.forEach((btn) => btn.classList.remove("active"));
      modePanels.forEach((panel) => panel.classList.remove("active-panel"));

      this.classList.add("active");

      const panel = document.getElementById(targetId);
      if (panel) {
        panel.classList.add("active-panel");
      }
    });
  });
}

// =========================
// HELPERS VISUALES
// =========================
function resumirHorario(horario) {
  if (!horario || horario.trim() === "") {
    return "No disponible";
  }

  const diasSemana = [
    "domingo",
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado"
  ];

  const hoy = new Date();
  const diaHoy = diasSemana[hoy.getDay()];
  const texto = horario.trim();

  if (texto.startsWith("{") && texto.endsWith("}")) {
    const regex = /'([^']+)'\s*:\s*'([^']*)'/g;
    let match;
    const mapa = {};

    while ((match = regex.exec(texto)) !== null) {
      const dia = match[1].trim().toLowerCase();
      const horas = match[2].trim();
      mapa[dia] = horas;
    }

    if (mapa[diaHoy]) {
      const horasHoy = mapa[diaHoy].trim();
      if (horasHoy === "" || horasHoy.toLowerCase() === "cerrado") {
        return "Cerrado";
      }
      return horasHoy;
    }

    return "No disponible";
  }

  const partes = texto.split("|").map((p) => p.trim()).filter(Boolean);

  for (const parte of partes) {
    const separador = parte.indexOf(":");
    if (separador === -1) continue;

    const dia = parte.slice(0, separador).trim().toLowerCase();
    const horas = parte.slice(separador + 1).trim();

    if (dia === diaHoy) {
      if (horas === "" || horas.toLowerCase() === "cerrado") {
        return "Cerrado";
      }
      return horas;
    }
  }

  return "No disponible";
}

function formatearTipo(types) {
  if (!types) return "No disponible";
  return String(types).replaceAll("|", ", ");
}

function truncarTexto(texto, maxLen = 170) {
  if (!texto) return "Sin descripción disponible.";

  const limpio = texto.trim();
  if (limpio.length <= maxLen) return limpio;

  return limpio.slice(0, maxLen) + "...";
}

function formatearValoracion(valor) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
    return "No disponible";
  }

  return `${Number(valor).toFixed(1)} ★`;
}

function obtenerImagenBar(bar) {
  if (bar.photo && String(bar.photo).trim() !== "") {
    return bar.photo;
  }

  return "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=800&q=80";
}

function obtenerLocalidadVisible(bar) {
  if (bar.zona && String(bar.zona).trim() !== "") {
    return bar.zona;
  }

  if (bar.ciudad && String(bar.ciudad).trim() !== "") {
    return bar.ciudad;
  }

  return "No disponible";
}

function normalizarPrecio(precio) {
  const valor = String(precio || "").trim().toLowerCase();

  if (
    valor === "" ||
    valor === "no disponible" ||
    valor === "null" ||
    valor === "undefined" ||
    valor === "nan" ||
    valor === "0" ||
    valor === "0€"
  ) {
    return "0€";
  }

  if (
    valor.includes("1-10") ||
    valor === "€" ||
    valor === "economico" ||
    valor === "económico" ||
    valor === "barato" ||
    valor === "price_level_inexpensive" ||
    valor === "low"
  ) {
    return "1-10€";
  }

  if (
    valor.includes("10-20") ||
    valor === "€€" ||
    valor === "medio" ||
    valor === "moderado" ||
    valor === "moderate" ||
    valor === "price_level_moderate"
  ) {
    return "10-20€";
  }

  if (
    valor.includes("20-30") ||
    valor === "€€€" ||
    valor === "alto" ||
    valor === "caro" ||
    valor === "expensive" ||
    valor === "price_level_expensive"
  ) {
    return "20-30€";
  }

  if (
    valor.includes("30-40") ||
    valor.includes("40-50") ||
    valor.includes("100") ||
    valor.includes("más de 30") ||
    valor.includes("mas de 30") ||
    valor === "€€€€" ||
    valor === "muy caro" ||
    valor === "very expensive" ||
    valor === "price_level_very_expensive"
  ) {
    return "Más de 30€";
  }

  return "0€";
}

// =========================
// RENDER
// =========================
function renderResultadoCard(bar, userId) {
  const article = document.createElement("article");
  article.className = "resultado-card";
  article.dataset.url = `bar.html?id=${bar.placeID}`;

  const favoritoActivo = esFavorito(bar.placeID);

  article.innerHTML = `
    <button class="favorito-btn ${favoritoActivo ? "active" : ""}" aria-label="${favoritoActivo ? "Quitar de favoritos" : "Añadir a favoritos"}">
      ${favoritoActivo ? "♥" : "♡"}
    </button>
    <img src="${obtenerImagenBar(bar)}" alt="${bar.nombre || "Bar"}">
    <div class="resultado-info">
      <h3>${bar.nombre || "Bar sin nombre"}</h3>
      <p><strong>Horario:</strong> ${resumirHorario(bar.opening_hours_weekday_text || "")}</p>
      <p><strong>Tipo:</strong> ${formatearTipo(bar.types)}</p>
      <p><strong>Localidad:</strong> ${obtenerLocalidadVisible(bar)}</p>
      <p><strong>Dirección:</strong> ${bar.calle || "No disponible"}</p>
      <p><strong>Precio:</strong> ${normalizarPrecio(bar.price_level)}</p>
      <p><strong>Valoración:</strong> ${formatearValoracion(bar.val_media)}</p>
      <p class="resultado-desc">${truncarTexto(bar.descripcion || bar.texto_semantico || "")}</p>
    </div>
  `;

  const favBtn = article.querySelector(".favorito-btn");

  favBtn.addEventListener("click", async function (event) {
    event.stopPropagation();

    if (!userId) {
      alert("Puedes buscar sin registrarte, pero para guardar favoritos debes iniciar sesión.");
      window.location.href = "login.html";
      return;
    }

    const estabaActivo = esFavorito(bar.placeID);
    const activar = !estabaActivo;

    const ok = await toggleFavoritoBackend(userId, bar.placeID, activar);

    if (!ok) {
      alert("No se pudo actualizar el favorito.");
      return;
    }

    let favoritos = obtenerFavoritos().map(Number);

    if (activar) {
      if (!favoritos.includes(Number(bar.placeID))) {
        favoritos.push(Number(bar.placeID));
      }
    } else {
      favoritos = favoritos.filter((id) => id !== Number(bar.placeID));
    }

    guardarFavoritos(favoritos);

    const activo = esFavorito(bar.placeID);
    this.classList.toggle("active", activo);
    this.textContent = activo ? "♥" : "♡";
    this.setAttribute("aria-label", activo ? "Quitar de favoritos" : "Añadir a favoritos");
  });

  article.addEventListener("click", function () {
    const url = this.dataset.url;
    if (url) {
      window.location.href = url;
    }
  });

  return article;
}

function pintarResultados(lista, userId) {
  resultadosGrid.innerHTML = "";

  if (!Array.isArray(lista) || lista.length === 0) {
    resultadosCount.textContent = "No se han encontrado resultados.";
    resultadosMessage.textContent = "";
    return;
  }

  lista.forEach((bar) => {
    resultadosGrid.appendChild(renderResultadoCard(bar, userId));
  });
}

// =========================
// CARGA DE OPCIONES DE FILTRO
// =========================
async function cargarOpcionesFiltrosResultados() {
  const filterType = document.getElementById("filterType");
  const filterZone = document.getElementById("filterZone");
  const filterPrice = document.getElementById("filterPrice");

  if (!filterType || !filterZone || !filterPrice) {
    return;
  }

  const valorTipoActual = filterType.value;
  const valorPrecioActual = filterPrice.value;
  const valorZonaActual = filterZone.value;

  filterType.innerHTML = "";
  TIPOS_FIJOS.forEach((tipo) => {
    const option = document.createElement("option");
    option.value = tipo.value;
    option.textContent = tipo.label;
    filterType.appendChild(option);
  });

  filterPrice.innerHTML = "";
  PRECIOS_FIJOS.forEach((precio) => {
    const option = document.createElement("option");
    option.value = precio.value;
    option.textContent = precio.label;
    filterPrice.appendChild(option);
  });

  try {
    const response = await fetch(`${BACKEND_URL}/filtros/opciones`);
    const data = await response.json();

    if (!response.ok || !data.ok) {
      filterZone.innerHTML = `<option value="">No disponible</option>`;
      filterType.value = valorTipoActual;
      filterPrice.value = valorPrecioActual;
      return;
    }

    filterZone.innerHTML = `<option value="">Todas</option>`;
    (data.zonas || []).forEach((zona) => {
      const option = document.createElement("option");
      option.value = zona;
      option.textContent = zona;
      filterZone.appendChild(option);
    });

    filterType.value = valorTipoActual;
    filterPrice.value = valorPrecioActual;
    filterZone.value = valorZonaActual;

  } catch (error) {
    console.error("Error cargando opciones de filtros:", error);
    filterZone.innerHTML = `<option value="">No disponible</option>`;
    filterType.value = valorTipoActual;
    filterPrice.value = valorPrecioActual;
  }
}

// =========================
// RECOMENDACIONES INICIALES
// =========================
async function cargarRecomendacionesIniciales() {
  const usuario = obtenerUsuarioValido();

  resultadosMessage.textContent = "";
  resultadosGrid.innerHTML = "";

  try {
    let response;

    if (usuario) {
      await sincronizarFavoritosDesdeBackend(usuario.user_id);
      response = await fetch(`${BACKEND_URL}/recomendaciones/${usuario.user_id}?limit=20`);
    } else {
      response = await fetch(`${BACKEND_URL}/recomendaciones-invitado?limit=20`);
    }

    const data = await response.json();

    if (!data.ok) {
      resultadosCount.textContent = "Error cargando recomendaciones.";
      resultadosMessage.textContent = data.mensaje || "Ha ocurrido un error.";
      resultadosGrid.innerHTML = "";
      return;
    }

    const recomendaciones = data.recomendaciones || [];

    resultadosMessage.textContent = data.mensaje || "";

    if (recomendaciones.length === 0) {
      resultadosCount.textContent = "No se han encontrado recomendaciones.";
      resultadosGrid.innerHTML = "";
      return;
    }

    resultadosCount.textContent = `Se han encontrado ${recomendaciones.length} bares.`;
    pintarResultados(recomendaciones, usuario ? usuario.user_id : null);

  } catch (error) {
    console.error(error);
    resultadosCount.textContent = "Error cargando recomendaciones.";
    resultadosMessage.textContent = "No se pudo conectar con el backend.";
    resultadosGrid.innerHTML = "";
  }
}

// =========================
// BÚSQUEDA SEMÁNTICA
// =========================
async function buscarPorDescripcionBackend(queryTexto) {
  const usuario = obtenerUsuarioValido();

  if (usuario) {
    await sincronizarFavoritosDesdeBackend(usuario.user_id);
  }

  resultadosCount.textContent = "Buscando bares por descripción...";
  resultadosMessage.textContent = "";
  resultadosGrid.innerHTML = "";

  try {
    const payload = {
      query: queryTexto,
      top_k: 20
    };

    if (usuario) {
      payload.user_id = usuario.user_id;
    }

    const response = await fetch(`${BACKEND_URL}/busqueda-semantic`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
      resultadosCount.textContent = "No se pudo completar la búsqueda.";
      resultadosMessage.textContent = data.mensaje || "Error en la búsqueda semántica.";
      resultadosGrid.innerHTML = "";
      return;
    }

    const recomendaciones = data.recomendaciones || [];
    resultadosCount.textContent = `Se han encontrado ${recomendaciones.length} bares según tu descripción.`;
    resultadosMessage.textContent = data.mensaje || "";
    pintarResultados(recomendaciones, usuario ? usuario.user_id : null);

  } catch (error) {
    console.error("Error en búsqueda semántica:", error);
    resultadosCount.textContent = "Error en la búsqueda.";
    resultadosMessage.textContent = "No se pudo conectar con el backend.";
    resultadosGrid.innerHTML = "";
  }
}

// =========================
// BÚSQUEDA POR FILTROS
// =========================
async function buscarPorFiltrosBackend({ type = "", zone = "", price = "", order = "relevancia" }) {
  const usuario = obtenerUsuarioValido();

  if (usuario) {
    await sincronizarFavoritosDesdeBackend(usuario.user_id);
  }

  resultadosCount.textContent = "Aplicando filtros...";
  resultadosMessage.textContent = "";
  resultadosGrid.innerHTML = "";

  try {
    const response = await fetch(`${BACKEND_URL}/buscar/filtros`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        type,
        zone,
        price,
        order,
        limit: 50
      })
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
      resultadosCount.textContent = "No se pudo completar la búsqueda por filtros.";
      resultadosMessage.textContent = data.mensaje || "Error en filtros.";
      resultadosGrid.innerHTML = "";
      return;
    }

    const recomendaciones = data.recomendaciones || [];
    resultadosCount.textContent = `Se han encontrado ${recomendaciones.length} bares tras aplicar filtros.`;
    resultadosMessage.textContent = data.mensaje || "";
    pintarResultados(recomendaciones, usuario ? usuario.user_id : null);

  } catch (error) {
    console.error("Error en búsqueda por filtros:", error);
    resultadosCount.textContent = "Error en la búsqueda.";
    resultadosMessage.textContent = "No se pudo conectar con el backend.";
    resultadosGrid.innerHTML = "";
  }
}

// =========================
// BUSCAR POR NOMBRE
// =========================
async function buscarPorNombreBackend(textoBusqueda) {
  const usuario = obtenerUsuarioValido();

  if (usuario) {
    await sincronizarFavoritosDesdeBackend(usuario.user_id);
  }

  resultadosCount.textContent = "Buscando bares por nombre...";
  resultadosMessage.textContent = "";
  resultadosGrid.innerHTML = "";

  try {
    const response = await fetch(`${BACKEND_URL}/buscar/nombre`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        texto: textoBusqueda,
        limit: 50
      })
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
      resultadosCount.textContent = "No se pudo completar la búsqueda por nombre.";
      resultadosMessage.textContent = data.mensaje || "Error en búsqueda por nombre.";
      resultadosGrid.innerHTML = "";
      return;
    }

    const recomendaciones = data.recomendaciones || [];
    resultadosCount.textContent = `Se han encontrado ${recomendaciones.length} bares por búsqueda de nombre.`;
    resultadosMessage.textContent = data.mensaje || "";
    pintarResultados(recomendaciones, usuario ? usuario.user_id : null);

  } catch (error) {
    console.error("Error en búsqueda por nombre:", error);
    resultadosCount.textContent = "Error en la búsqueda.";
    resultadosMessage.textContent = "No se pudo conectar con el backend.";
    resultadosGrid.innerHTML = "";
  }
}

// =========================
// FORMULARIO NOMBRE
// =========================
function inicializarFormularioNombre() {
  const form = document.getElementById("resultsByName");
  const input = document.getElementById("resultsName");

  if (!form || !input) {
    return;
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const texto = input.value.trim();

    if (texto === "") {
      resultadosCount.textContent = "Debes escribir un nombre para buscar.";
      resultadosMessage.textContent = "";
      resultadosGrid.innerHTML = "";
      return;
    }

    const nuevaUrl = `resultados.html?modo=nombre&texto=${encodeURIComponent(texto)}`;
    window.history.replaceState({}, "", nuevaUrl);

    await buscarPorNombreBackend(texto);
  });
}

// =========================
// FORMULARIO FILTROS
// =========================
function inicializarFormularioFiltros() {
  const form = document.getElementById("resultsByFilters");
  if (!form) return;

  form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const typeValue = document.getElementById("filterType")?.value.trim() || "";
    const zoneValue = document.getElementById("filterZone")?.value.trim() || "";
    const priceValue = document.getElementById("filterPrice")?.value.trim() || "";
    const orderValue = document.getElementById("filterOrder")?.value.trim() || "relevancia";

    const nuevaUrl = `resultados.html?modo=filtros&type=${encodeURIComponent(typeValue)}&zone=${encodeURIComponent(zoneValue)}&price=${encodeURIComponent(priceValue)}&order=${encodeURIComponent(orderValue)}`;
    window.history.replaceState({}, "", nuevaUrl);

    await buscarPorFiltrosBackend({
      type: typeValue,
      zone: zoneValue,
      price: priceValue,
      order: orderValue
    });
  });

  form.addEventListener("reset", function () {
    setTimeout(async () => {
      window.history.replaceState({}, "", "resultados.html");
      await cargarOpcionesFiltrosResultados();
      await cargarRecomendacionesIniciales();
    }, 0);
  });
}

// =========================
// FORMULARIO DESCRIPCIÓN
// =========================
function inicializarFormularioDescripcion() {
  const form = document.getElementById("resultsByDescription");
  const resultsText = document.getElementById("resultsText");
  const resultsTextError = document.getElementById("resultsTextError");

  if (!form || !resultsText || !resultsTextError) return;

  const queryInicial = obtenerParametroURL("query");
  const modoInicial = obtenerParametroURL("modo");

  if (modoInicial === "descripcion" && queryInicial) {
    resultsText.value = queryInicial;

    document.querySelectorAll(".search-mode-btn").forEach((btn) => btn.classList.remove("active"));
    document.querySelectorAll(".search-mode-panel").forEach((panel) => panel.classList.remove("active-panel"));

    const botonDescripcion = document.querySelector('.search-mode-btn[data-target="resultsByDescription"]');
    const panelDescripcion = document.getElementById("resultsByDescription");

    if (botonDescripcion) botonDescripcion.classList.add("active");
    if (panelDescripcion) panelDescripcion.classList.add("active-panel");
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const text = resultsText.value.trim();
    const wordCount = contarPalabras(text);

    resultsTextError.textContent = "";

    if (wordCount < 20) {
      resultsTextError.textContent = "Debes escribir al menos 20 palabras para describir lo que buscas.";
      return;
    }

    const nuevaUrl = `resultados.html?modo=descripcion&query=${encodeURIComponent(text)}`;
    window.history.replaceState({}, "", nuevaUrl);

    await buscarPorDescripcionBackend(text);
  });
}

// =========================
// INIT
// =========================
document.addEventListener("DOMContentLoaded", async function () {

  inicializarMenus();
  inicializarTabs();
  inicializarFormularioNombre();
  inicializarFormularioFiltros();
  inicializarFormularioDescripcion();

  await cargarOpcionesFiltrosResultados();

  const modo = obtenerParametroURL("modo");
  const query = obtenerParametroURL("query");
  const textoNombre = obtenerParametroURL("texto") || "";
  const type = obtenerParametroURL("type") || "";
  const zone = obtenerParametroURL("zone") || "";
  const price = obtenerParametroURL("price") || "";
  const order = obtenerParametroURL("order") || "relevancia";

  const resultsName = document.getElementById("resultsName");
  const filterType = document.getElementById("filterType");
  const filterZone = document.getElementById("filterZone");
  const filterPrice = document.getElementById("filterPrice");
  const filterOrder = document.getElementById("filterOrder");

  if (resultsName) resultsName.value = textoNombre;
  if (filterType) filterType.value = type;
  if (filterZone) filterZone.value = zone;
  if (filterPrice) filterPrice.value = price;
  if (filterOrder) filterOrder.value = order;

  if (modo === "nombre" && textoNombre.trim() !== "") {
    document.querySelectorAll(".search-mode-btn").forEach((btn) => btn.classList.remove("active"));
    document.querySelectorAll(".search-mode-panel").forEach((panel) => panel.classList.remove("active-panel"));

    const botonNombre = document.querySelector('.search-mode-btn[data-target="resultsByName"]');
    const panelNombre = document.getElementById("resultsByName");

    if (botonNombre) botonNombre.classList.add("active");
    if (panelNombre) panelNombre.classList.add("active-panel");

    await buscarPorNombreBackend(textoNombre);
    return;
  }

  if (modo === "descripcion" && query && contarPalabras(query) >= 20) {
    await buscarPorDescripcionBackend(query);
    return;
  }

  if (modo === "filtros") {
    document.querySelectorAll(".search-mode-btn").forEach((btn) => btn.classList.remove("active"));
    document.querySelectorAll(".search-mode-panel").forEach((panel) => panel.classList.remove("active-panel"));

    const botonFiltros = document.querySelector('.search-mode-btn[data-target="resultsByFilters"]');
    const panelFiltros = document.getElementById("resultsByFilters");

    if (botonFiltros) botonFiltros.classList.add("active");
    if (panelFiltros) panelFiltros.classList.add("active-panel");

    await buscarPorFiltrosBackend({
      type,
      zone,
      price,
      order
    });
    return;
  }

  await cargarRecomendacionesIniciales();
});
