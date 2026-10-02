var BACKEND_URL = window.BACKEND_URL || "";

const carouselValorados = document.getElementById("barCarouselValorados");
const carouselVisitados = document.getElementById("barCarouselVisitados");

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

// =========================
// SCROLL CARRUSELES
// =========================
function inicializarScrollCarrusel(carouselId, leftBtnId, rightBtnId) {
  const carousel = document.getElementById(carouselId);
  const leftBtn = document.getElementById(leftBtnId);
  const rightBtn = document.getElementById(rightBtnId);

  if (leftBtn && carousel) {
    leftBtn.addEventListener("click", function () {
      carousel.scrollBy({ left: -320, behavior: "smooth" });
    });
  }

  if (rightBtn && carousel) {
    rightBtn.addEventListener("click", function () {
      carousel.scrollBy({ left: 320, behavior: "smooth" });
    });
  }
}

// =========================
// TABS DE BÚSQUEDA
// =========================
function inicializarTabsBusqueda() {
  const modeButtons = document.querySelectorAll(".search-mode-btn");
  const modePanels = document.querySelectorAll(".search-mode-panel");

  modeButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const targetId = this.dataset.target;

      modeButtons.forEach((btn) => btn.classList.remove("active"));
      modePanels.forEach((panel) => panel.classList.remove("active-panel"));

      this.classList.add("active");

      const panelObjetivo = document.getElementById(targetId);
      if (panelObjetivo) {
        panelObjetivo.classList.add("active-panel");
      }
    });
  });
}

// =========================
// HELPERS
// =========================
function formatearTipos(types) {
  if (!types) return typeof t === "function" ? t("no_especificado") : "No especificado";

  if (Array.isArray(types)) {
    return types.length > 0 ? types.join(", ") : (typeof t === "function" ? t("no_especificado") : "No especificado");
  }

  if (typeof types === "string") {
    return types.replaceAll("|", ", ");
  }

  return typeof t === "function" ? t("no_especificado") : "No especificado";
}

function formatearHorario(horarios) {
  if (!horarios) return typeof t === "function" ? t("no_disponible") : "No disponible";

  if (Array.isArray(horarios)) {
    return horarios.length > 0 ? horarios[0] : (typeof t === "function" ? t("no_disponible") : "No disponible");
  }

  if (typeof horarios === "string") {
    const partes = horarios.split("|").map((p) => p.trim()).filter(Boolean);
    return partes.length > 0 ? partes[0] : (typeof t === "function" ? t("no_disponible") : "No disponible");
  }

  return typeof t === "function" ? t("no_disponible") : "No disponible";
}

function contarPalabras(texto) {
  const limpio = (texto || "").trim();
  if (limpio === "") return 0;
  return limpio.split(/\s+/).length;
}

function obtenerImagenBar(bar) {
  if (bar.photo && String(bar.photo).trim() !== "") {
    return String(bar.photo).trim();
  }

  return "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=800&q=80";
}

// =========================
// FAVORITOS
// =========================
async function obtenerFavoritosUsuario(userId) {
  try {
    const response = await fetch(`${BACKEND_URL}/favoritos/${userId}`);
    const data = await response.json();

    if (!response.ok || !data.ok) return [];
    return data.favoritos || [];
  } catch (error) {
    console.error("Error obteniendo favoritos:", error);
    return [];
  }
}

function crearBarCard(bar, favoritosUsuario) {
  const esFavorito = favoritosUsuario.includes(Number(bar.placeID));
  const corazon = esFavorito ? "♥" : "♡";
  const claseFavorito = esFavorito ? "favorito-btn active" : "favorito-btn";

  const article = document.createElement("article");
  article.className = "bar-card";
  article.dataset.id = bar.placeID;

  article.innerHTML = `
    <button class="${claseFavorito}" aria-label="Favorito">${corazon}</button>
    <img src="${obtenerImagenBar(bar)}" alt="${bar.nombre}">
    <div class="bar-info">
      <h3>${bar.nombre}</h3>
      <p><strong>${typeof t === "function" ? t("horario") : "Horario:"}</strong> ${formatearHorario(bar.opening_hours_weekday_text)}</p>
      <p><strong>${typeof t === "function" ? t("tipo") : "Tipo:"}</strong> ${formatearTipos(bar.types)}</p>
    </div>
  `;

  article.addEventListener("click", function () {
    window.location.href = `bar.html?id=${bar.placeID}`;
  });

  const favoritoBtn = article.querySelector(".favorito-btn");
  favoritoBtn.addEventListener("click", async function (event) {
    event.stopPropagation();

    const usuarioLogueado = obtenerUsuarioLogueado();

    if (!usuarioLogueado) {
      if (typeof t === "function") {
        alert(t("login_favoritos"));
      } else {
        alert("Debes iniciar sesión para añadir favoritos.");
      }
      window.location.href = "login.html";
      return;
    }

    const placeID = Number(bar.placeID);
    const userId = Number(usuarioLogueado.user_id);
    const favoritoActivo = this.classList.contains("active");

    try {
      if (favoritoActivo) {
        const response = await fetch(`${BACKEND_URL}/favoritos`, {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: userId,
            placeID: placeID
          })
        });

        const data = await response.json();

        if (!response.ok || !data.ok) {
          alert(data.mensaje || (typeof t === "function" ? t("error_eliminar_favorito") : "No se pudo eliminar el favorito."));
          return;
        }

        this.classList.remove("active");
        this.textContent = "♡";
      } else {
        const response = await fetch(`${BACKEND_URL}/favoritos`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: userId,
            placeID: placeID
          })
        });

        const data = await response.json();

        if (!response.ok || !data.ok) {
          alert(data.mensaje || (typeof t === "function" ? t("error_guardar_favorito") : "No se pudo guardar el favorito."));
          return;
        }

        this.classList.add("active");
        this.textContent = "♥";
      }
    } catch (error) {
      console.error("Error actualizando favorito:", error);
      alert(typeof t === "function" ? t("error_servidor") : "No se pudo conectar con el servidor.");
    }
  });

  return article;
}

// =========================
// PINTAR CARRUSELES
// =========================
function pintarCarrusel(contenedor, bares, favoritosUsuario) {
  if (!contenedor) return;

  contenedor.innerHTML = "";
  bares.forEach((bar) => {
    contenedor.appendChild(crearBarCard(bar, favoritosUsuario));
  });
}

async function cargarCarruselesInicio() {
  try {
    const response = await fetch("/data/jaen/json/bares_enriquecidos.json");
    const bares = await response.json();

    const usuario = obtenerUsuarioLogueado();
    const favoritosUsuario = usuario ? await obtenerFavoritosUsuario(usuario.user_id) : [];

    const baresMejorValorados = [...bares]
      .filter((bar) => bar.val_media !== undefined && bar.val_media !== null && !isNaN(Number(bar.val_media)))
      .sort((a, b) => Number(b.val_media) - Number(a.val_media))
      .slice(0, 10);

    const baresMasVisitados = [...bares]
      .filter((bar) => bar.num_val !== undefined && bar.num_val !== null && !isNaN(Number(bar.num_val)))
      .sort((a, b) => Number(b.num_val) - Number(a.num_val))
      .slice(0, 15);

    pintarCarrusel(carouselValorados, baresMejorValorados, favoritosUsuario);
    pintarCarrusel(carouselVisitados, baresMasVisitados, favoritosUsuario);

  } catch (error) {
    console.error("Error cargando carruseles:", error);
  }
}

// =========================
// BÚSQUEDA POR NOMBRE
// =========================
function inicializarBusquedaPorNombreInicio() {
  const form = document.getElementById("searchByName");
  const input = document.getElementById("barName");

  if (!form || !input) return;

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    const texto = input.value.trim();
    if (texto === "") return;

    window.location.href = `/web/html/resultados.html?modo=nombre&texto=${encodeURIComponent(texto)}`;
  });
}

// =========================
// BÚSQUEDA POR DESCRIPCIÓN
// =========================
function inicializarBusquedaPorDescripcion() {
  const form = document.getElementById("searchByDescription");
  const userText = document.getElementById("userText");
  const textError = document.getElementById("textError");

  if (!form || !userText || !textError) return;

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    const texto = userText.value.trim();
    const numPalabras = contarPalabras(texto);

    textError.textContent = "";

    if (numPalabras < 20) {
      textError.textContent = typeof t === "function"
        ? t("error_20_palabras")
        : "Debes escribir al menos 20 palabras.";
      return;
    }

    window.location.href = `/web/html/resultados.html?modo=descripcion&query=${encodeURIComponent(texto)}`;
  });
}

// =========================
// OPCIONES DE FILTROS
// =========================
async function cargarOpcionesFiltrosInicio() {
  const typeFilter = document.getElementById("typeFilter");
  const zoneFilter = document.getElementById("zoneFilter");
  const priceFilter = document.getElementById("priceFilter");

  if (!typeFilter || !zoneFilter || !priceFilter) return;

  typeFilter.innerHTML = "";
  TIPOS_FIJOS.forEach((tipo) => {
    const option = document.createElement("option");
    option.value = tipo.value;
    option.textContent = tipo.label;
    typeFilter.appendChild(option);
  });

  priceFilter.innerHTML = "";
  PRECIOS_FIJOS.forEach((precio) => {
    const option = document.createElement("option");
    option.value = precio.value;
    option.textContent = precio.label;
    priceFilter.appendChild(option);
  });

  try {
    const response = await fetch(`${BACKEND_URL}/filtros/opciones`);
    const data = await response.json();

    if (!response.ok || !data.ok) {
      zoneFilter.innerHTML = `<option value="">${typeof t === "function" ? t("no_disponible") : "No disponible"}</option>`;
      return;
    }

    zoneFilter.innerHTML = `<option value="">Todas</option>`;
    (data.zonas || []).forEach((zona) => {
      const option = document.createElement("option");
      option.value = zona;
      option.textContent = zona;
      zoneFilter.appendChild(option);
    });

  } catch (error) {
    console.error("Error cargando opciones de filtros:", error);
    zoneFilter.innerHTML = `<option value="">${typeof t === "function" ? t("no_disponible") : "No disponible"}</option>`;
  }
}

// =========================
// BÚSQUEDA POR FILTROS
// =========================
function inicializarBusquedaPorFiltrosInicio() {
  const form = document.getElementById("searchByFilters");
  if (!form) return;

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    const type = document.getElementById("typeFilter")?.value?.trim() || "";
    const zone = document.getElementById("zoneFilter")?.value?.trim() || "";
    const price = document.getElementById("priceFilter")?.value?.trim() || "";

    window.location.href = `/web/html/resultados.html?modo=filtros&type=${encodeURIComponent(type)}&zone=${encodeURIComponent(zone)}&price=${encodeURIComponent(price)}&order=relevancia`;
  });
}

// =========================
// IDIOMA
// =========================
function aplicarIdiomaInicio() {
  if (typeof aplicarTraduccionesDOM === "function") {
    aplicarTraduccionesDOM();
  }
  cargarOpcionesFiltrosInicio();
  cargarCarruselesInicio();
}

// =========================
// INIT
// =========================
document.addEventListener("DOMContentLoaded", function () {
  inicializarTabsBusqueda();
  inicializarBusquedaPorNombreInicio();
  inicializarBusquedaPorDescripcion();
  inicializarBusquedaPorFiltrosInicio();

  inicializarScrollCarrusel("barCarouselValorados", "scrollLeftValorados", "scrollRightValorados");
  inicializarScrollCarrusel("barCarouselVisitados", "scrollLeftVisitados", "scrollRightVisitados");

  aplicarIdiomaInicio();
});

document.addEventListener("idiomaCambiado", function () {
  aplicarIdiomaInicio();
});