console.log("bar.js cargado");
var BACKEND_URL = window.BACKEND_URL || "";

const stars = document.querySelectorAll(".star");
const reviewForm = document.getElementById("reviewForm");
const reviewText = document.getElementById("reviewText");
const starsError = document.getElementById("starsError");
const reviewError = document.getElementById("reviewError");

let selectedRating = 0;
let barActual = null;

// =========================
// SESIÓN
// =========================
function obtenerUsuarioLogueado() {
  const usuario = localStorage.getItem("usuarioLogueado");
  return usuario ? JSON.parse(usuario) : null;
}

// =========================
// HELPERS SEGUROS
// =========================
function setText(id, value, fallback = "No disponible") {
  const el = document.getElementById(id);
  if (!el) return;

  const texto = value !== undefined && value !== null ? String(value).trim() : "";
  el.textContent = texto !== "" ? texto : fallback;
}

function setImage(id, src, alt = "") {
  const el = document.getElementById(id);
  if (!el) return;

  const fallback = "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=800&q=80";
  const finalSrc = src && String(src).trim() !== "" ? String(src).trim() : fallback;

  el.src = finalSrc;
  el.alt = alt || "Imagen del bar";

  el.onerror = function () {
    this.src = fallback;
  };
}

function setLink(id, url) {
  const el = document.getElementById(id);
  if (!el) return;

  if (url && String(url).trim() !== "") {
    const urlLimpia = String(url).trim();

    try {
      const parsed = new URL(urlLimpia);
      el.textContent = parsed.hostname;
    } catch {
      el.textContent = "Visitar web";
    }

    el.href = urlLimpia;
    el.target = "_blank";
    el.rel = "noopener noreferrer";
  } else {
    el.textContent = "No disponible";
    el.removeAttribute("href");
    el.removeAttribute("target");
    el.removeAttribute("rel");
  }
}

function formatearTipos(types) {
  if (!types || types.length === 0) return "No especificado";
  return types.join(", ");
}

function formatearHorarios(horarios) {
  if (!horarios) return "No disponible";

  if (Array.isArray(horarios)) {
    return horarios.join(" | ");
  }

  if (typeof horarios === "string") {
    return horarios.split("|").map(h => h.trim()).join(" | ");
  }

  return "No disponible";
}

function formatearPrecio(priceLevel) {
  const mapa = {
    economico: "€ - Económico",
    medio: "€€ - Medio",
    alto: "€€€ - Alto",
    muy_alto: "€€€€ - Muy alto"
  };

  return mapa[priceLevel] || priceLevel || "No disponible";
}

function estrellasDesdeRating(rating) {
  const redondeado = Math.round(Number(rating));
  let resultado = "";

  for (let i = 1; i <= 5; i++) {
    resultado += i <= redondeado ? "★" : "☆";
  }

  return resultado;
}

function formatearFecha(fechaIso) {
  if (!fechaIso) return "";
  const fecha = new Date(fechaIso);
  if (isNaN(fecha.getTime())) return fechaIso;
  return fecha.toLocaleDateString("es-ES");
}

// =========================
// ESTRELLAS DE VALORACIÓN
// =========================
stars.forEach((star) => {
  star.addEventListener("mouseover", function () {
    const value = parseInt(this.dataset.value);
    highlightStars(value);
  });

  star.addEventListener("click", function () {
    selectedRating = parseInt(this.dataset.value);
    highlightStars(selectedRating);
  });
});

const starSelector = document.getElementById("starSelector");
if (starSelector) {
  starSelector.addEventListener("mouseleave", function () {
    highlightStars(selectedRating);
  });
}

function highlightStars(value) {
  stars.forEach((star) => {
    const starValue = parseInt(star.dataset.value);
    if (starValue <= value) {
      star.classList.add("active");
    } else {
      star.classList.remove("active");
    }
  });
}

// =========================
// OPINIONES
// =========================
function pintarOpiniones(opiniones) {
  const opinionesList = document.getElementById("opinionesList");
  if (!opinionesList) return;

  opinionesList.innerHTML = "";

  if (!opiniones || opiniones.length === 0) {
    opinionesList.innerHTML = "<p>No hay opiniones todavía.</p>";
    return;
  }

  opiniones.forEach((opinion) => {
    const article = document.createElement("article");
    article.className = "opinion-card";

    article.innerHTML = `
      <div class="opinion-header">
        <div>
          <h3>${opinion.username || "Usuario"}</h3>
          <p class="opinion-stars">${estrellasDesdeRating(opinion.rating)}</p>
        </div>
        <span class="opinion-date">${formatearFecha(opinion.fecha_publicacion)}</span>
      </div>
      <p class="opinion-text">${opinion.text || ""}</p>
    `;

    opinionesList.appendChild(article);
  });
}

function actualizarValoracionMedia(opiniones, valorPorDefecto = 0, numValPorDefecto = 0) {
  const numeroOpiniones = opiniones.length;

  if (numeroOpiniones === 0) {
    setText("barValoracionNumero", Number(valorPorDefecto || 0).toFixed(1), "0.0");
    setText("barValoracionStars", estrellasDesdeRating(valorPorDefecto || 0), "☆☆☆☆☆");
    setText("barValoracionCount", `Basada en ${numValPorDefecto || 0} opiniones`);
    return;
  }

  const suma = opiniones.reduce((acc, op) => acc + Number(op.rating || 0), 0);
  const media = suma / numeroOpiniones;

  setText("barValoracionNumero", media.toFixed(1), "0.0");
  setText("barValoracionStars", estrellasDesdeRating(media), "☆☆☆☆☆");
  setText("barValoracionCount", `Basada en ${numeroOpiniones} opiniones`);
}

async function cargarOpinionesBar(placeID) {
  try {
    const response = await fetch(`${BACKEND_URL}/opiniones/${placeID}`);
    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.mensaje || "Error cargando opiniones.");
    }

    const opiniones = data.opiniones || [];
    pintarOpiniones(opiniones);

    if (barActual) {
      actualizarValoracionMedia(opiniones, barActual.val_media, barActual.num_val);
    }

    const usuario = obtenerUsuarioLogueado();
    if (usuario && usuario.user_id) {
      const yaOpino = usuarioYaOpinoEnEsteBar(opiniones, usuario.user_id);

      if (yaOpino) {
        desactivarFormularioOpinion("Ya escribiste una opinión sobre este local.");
      } else {
        activarFormularioOpinion();
      }
    } else {
      activarFormularioOpinion();
    }

  } catch (error) {
    console.error("Error cargando opiniones del bar:", error);
    pintarOpiniones([]);
    if (barActual) {
      actualizarValoracionMedia([], barActual.val_media, barActual.num_val);
    }
  }
}

// =========================
// FAVORITOS BACKEND
// =========================
async function obtenerFavoritosUsuario(userId) {
  try {
    const response = await fetch(`${BACKEND_URL}/favoritos/${userId}`);
    const data = await response.json();

    if (!response.ok || !data.ok) {
      return [];
    }

    return data.favoritos || [];
  } catch (error) {
    console.error("Error obteniendo favoritos:", error);
    return [];
  }
}

async function esFavoritoBackend(userId, placeID) {
  const favoritos = await obtenerFavoritosUsuario(userId);
  return favoritos.includes(Number(placeID));
}

function crearBotonFavoritoDetalle(bar) {
  const detalleInfoContainer = document.querySelector(".detalle-info-container");
  if (!detalleInfoContainer) return;

  const botonExistente = document.getElementById("detalleFavoritoBtn");
  if (botonExistente) botonExistente.remove();

  const boton = document.createElement("button");
  boton.id = "detalleFavoritoBtn";
  boton.className = "favorito-btn";
  boton.textContent = "♡";
  boton.setAttribute("aria-label", "Favorito");
  boton.style.marginBottom = "16px";

  const usuario = obtenerUsuarioLogueado();

  if (usuario) {
    esFavoritoBackend(usuario.user_id, bar.placeID).then((esFavorito) => {
      if (esFavorito) {
        boton.classList.add("active");
        boton.textContent = "♥";
      }
    });
  }

  boton.addEventListener("click", async function () {
    const usuarioLogueado = obtenerUsuarioLogueado();
    if (!usuarioLogueado) {
      alert("Debes iniciar sesión para añadir favoritos.");
      window.location.href = "login.html";
      return;
    }

    const placeID = Number(bar.placeID);
    const userId = Number(usuarioLogueado.user_id);
    const favoritoActivo = boton.classList.contains("active");

    try {
      if (favoritoActivo) {
        const response = await fetch(`${BACKEND_URL}/favoritos`, {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            user_id: userId,
            placeID: placeID
          })
        });

        const data = await response.json();

        if (!response.ok || !data.ok) {
          alert(data.mensaje || "No se pudo eliminar el favorito.");
          return;
        }

        boton.classList.remove("active");
        boton.textContent = "♡";
      } else {
        const response = await fetch(`${BACKEND_URL}/favoritos`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            user_id: userId,
            placeID: placeID
          })
        });

        const data = await response.json();

        if (!response.ok || !data.ok) {
          alert(data.mensaje || "No se pudo guardar el favorito.");
          return;
        }

        boton.classList.add("active");
        boton.textContent = "♥";
      }
    } catch (error) {
      console.error("Error actualizando favorito:", error);
      alert("No se pudo conectar con el servidor.");
    }
  });

  detalleInfoContainer.insertBefore(boton, detalleInfoContainer.firstChild);
}

// =========================
// ENVÍO DE OPINIÓN
// =========================
if (reviewForm && reviewText && starsError && reviewError) {
  reviewForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const usuario = obtenerUsuarioLogueado();
    if (!usuario) {
      alert("Debes iniciar sesión para escribir una opinión.");
      window.location.href = "login.html";
      return;
    }
    
    const opinionesExistentes = document.querySelectorAll(".opinion-card");
    if (reviewText.disabled) {
      alert("Ya has escrito una opinión sobre este bar.");
      return;
    }

    let isValid = true;
    starsError.textContent = "";
    reviewError.textContent = "";

    if (selectedRating === 0) {
      starsError.textContent = "Debes seleccionar una valoración en estrellas.";
      isValid = false;
    }

    if (reviewText.value.trim() === "") {
      reviewError.textContent = "Debes escribir un comentario antes de enviarlo.";
      isValid = false;
    }

    if (!isValid || !barActual) {
      return;
    }

    try {
      const response = await fetch(`${BACKEND_URL}/opiniones`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          placeID: Number(barActual.placeID),
          user_id: Number(usuario.user_id),
          rating: Number(selectedRating),
          text: reviewText.value.trim()
        })
      });

      const data = await response.json();

      if (!response.ok || !data.ok) {
        alert(data.mensaje || "No se pudo guardar la opinión.");
        return;
      }

      alert("Opinión enviada correctamente.");
      reviewForm.reset();
      selectedRating = 0;
      highlightStars(0);

      await cargarOpinionesBar(barActual.placeID);
    } catch (error) {
      console.error("Error enviando opinión:", error);
      alert("No se pudo conectar con el servidor.");
    }
  });
}

// =========================
// CARGA DINÁMICA DEL BAR
// =========================
async function cargarBar() {
  try {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("id");

    const response = await fetch("/data/jaen/json/bares_enriquecidos.json");
    const bares = await response.json();

    const bar = bares.find((b) => String(b.placeID) === String(id));

    if (!bar) {
      const detalleMain = document.querySelector(".detalle-main");
      if (detalleMain) detalleMain.innerHTML = "<h1>Bar no encontrado</h1>";
      return;
    }

    barActual = bar;

    setText("barNombre", bar.nombre, "Sin nombre");
    setImage("barImagen", bar.photo, bar.nombre || "Imagen del bar");
    setText("barHorario", formatearHorarios(bar.opening_hours_weekday_text));
    setLink("barWeb", bar.website);

    setText("barTipo", formatearTipos(bar.types));
    setText("barLocalizacion", bar.ciudad);
    setText("barCalle", bar.calle);
    setText("barMunicipio", bar.ciudad);
    setText("barPrecio", formatearPrecio(bar.price_level));
    setText("barDescripcion", bar.descripcion);

    crearBotonFavoritoDetalle(bar);

    await cargarOpinionesBar(bar.placeID);
  } catch (error) {
    console.error("Error cargando bar:", error);
    const detalleMain = document.querySelector(".detalle-main");
    if (detalleMain) detalleMain.innerHTML = "<h1>Error cargando el bar</h1>";
  }
}
function desactivarFormularioOpinion(mensaje = "Ya escribiste una opinión sobre este local.") {
  const reviewForm = document.getElementById("reviewForm");
  const reviewText = document.getElementById("reviewText");
  const starSelector = document.getElementById("starSelector");

  if (!reviewForm) return;

  let aviso = document.getElementById("reviewFormAviso");
  if (!aviso) {
    aviso = document.createElement("p");
    aviso.id = "reviewFormAviso";
    aviso.className = "error-message";
    aviso.style.marginTop = "12px";
    reviewForm.prepend(aviso);
  }

  aviso.textContent = mensaje;

  if (reviewText) {
    reviewText.value = mensaje;
    reviewText.disabled = true;
  }

  if (starSelector) {
    starSelector.style.pointerEvents = "none";
    starSelector.style.opacity = "0.5";
  }

  const submitBtn = reviewForm.querySelector('button[type="submit"]');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Opinión ya enviada";
  }
}

function activarFormularioOpinion() {
  const reviewForm = document.getElementById("reviewForm");
  const reviewText = document.getElementById("reviewText");
  const starSelector = document.getElementById("starSelector");

  if (!reviewForm) return;

  const aviso = document.getElementById("reviewFormAviso");
  if (aviso) {
    aviso.textContent = "";
  }

  if (reviewText) {
    reviewText.disabled = false;
    reviewText.value = "";
  }

  if (starSelector) {
    starSelector.style.pointerEvents = "";
    starSelector.style.opacity = "";
  }

  const submitBtn = reviewForm.querySelector('button[type="submit"]');
  if (submitBtn) {
    submitBtn.disabled = false;
    submitBtn.textContent = "Enviar opinión";
  }
}

function usuarioYaOpinoEnEsteBar(opiniones, userId) {
  if (!Array.isArray(opiniones) || !userId) return false;

  return opiniones.some((op) => Number(op.user_id) === Number(userId));
}

cargarBar();