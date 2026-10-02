var BACKEND_URL = window.BACKEND_URL || "";

const perfilAvatar = document.getElementById("perfilAvatar");
const perfilNombre = document.getElementById("perfilNombre");
const perfilEmail = document.getElementById("perfilEmail");

const perfilOpinionesList = document.getElementById("perfilOpinionesList");
const perfilDestacadosGrid = document.getElementById("perfilDestacadosGrid");

const opinionesUp = document.getElementById("opinionesUp");
const opinionesDown = document.getElementById("opinionesDown");

function obtenerUsuarioLogueado() {
  const usuario = localStorage.getItem("usuarioLogueado");
  if (!usuario) return null;

  try {
    return JSON.parse(usuario);
  } catch (error) {
    console.error("Error parseando usuarioLogueado:", error);
    return null;
  }
}

function requireLogin() {
  const usuario = obtenerUsuarioLogueado();

  if (!usuario) {
    window.location.href = "login.html";
    return null;
  }

  return usuario;
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

  const idioma = obtenerIdiomaActual() === "en" ? "en-GB" : "es-ES";
  return fecha.toLocaleDateString(idioma);
}

function formatearTipos(types) {
  if (!types || types.length === 0) return t("no_especificado");
  return Array.isArray(types) ? types.join(", ") : String(types).replaceAll("|", ", ");
}

function formatearHorario(horarios) {
  if (!horarios || horarios.length === 0) return t("no_disponible");
  if (Array.isArray(horarios)) return horarios[0];
  if (typeof horarios === "string") {
    const partes = horarios.split("|").map((p) => p.trim()).filter(Boolean);
    return partes.length > 0 ? partes[0] : t("no_disponible");
  }
  return t("no_disponible");
}

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

async function obtenerOpinionesUsuario(userId) {
  try {
    const response = await fetch(`${BACKEND_URL}/opiniones/usuario/${userId}`);
    const data = await response.json();

    if (!response.ok || !data.ok) return [];
    return data.opiniones || [];
  } catch (error) {
    console.error("Error obteniendo opiniones del usuario:", error);
    return [];
  }
}

function pintarDatosUsuario(usuario) {
  perfilNombre.textContent =
    usuario.username && String(usuario.username).trim() !== ""
      ? usuario.username
      : t("perfil_default_name");

  perfilEmail.textContent =
    usuario.email && String(usuario.email).trim() !== ""
      ? usuario.email
      : t("perfil_sin_email");

  const inicial =
    usuario.username && String(usuario.username).trim() !== ""
      ? usuario.username.charAt(0).toUpperCase()
      : "U";

  perfilAvatar.textContent = inicial;
}

async function pintarOpinionesUsuario(usuario, bares) {
  if (!perfilOpinionesList) return;

  perfilOpinionesList.innerHTML = "";

  const opinionesUsuario = await obtenerOpinionesUsuario(usuario.user_id);

  if (opinionesUsuario.length === 0) {
    perfilOpinionesList.innerHTML = `<p>${t("perfil_no_opiniones")}</p>`;
    return;
  }

  opinionesUsuario.forEach((opinion) => {
    const bar = bares.find((b) => Number(b.placeID) === Number(opinion.placeID));
    const nombreBar = bar ? bar.nombre : `Bar ${opinion.placeID}`;

    const article = document.createElement("article");
    article.className = "perfil-opinion-card";

    article.innerHTML = `
      <div class="perfil-opinion-top">
        <div>
          <h3>${nombreBar}</h3>
          <p class="perfil-opinion-stars">${estrellasDesdeRating(opinion.rating)}</p>
        </div>
        <span class="perfil-opinion-date">${formatearFecha(opinion.fecha_publicacion)}</span>
      </div>
      <p class="perfil-opinion-text">${opinion.text || ""}</p>
    `;

    perfilOpinionesList.appendChild(article);
  });
}

async function pintarFavoritos(usuario, bares) {
  if (!perfilDestacadosGrid) return;

  perfilDestacadosGrid.innerHTML = "";

  const favoritos = await obtenerFavoritosUsuario(usuario.user_id);
  const baresFavoritos = bares.filter((bar) => favoritos.includes(Number(bar.placeID)));

  if (baresFavoritos.length === 0) {
    perfilDestacadosGrid.innerHTML = `<p>${t("perfil_no_favoritos")}</p>`;
    return;
  }

  baresFavoritos.forEach((bar) => {
    const article = document.createElement("article");
    article.className = "perfil-destacado-card";

    article.innerHTML = `
      <button class="favorito-btn active" aria-label="${t("quitar_favoritos")}">♥</button>
      <img src="${bar.photo}" alt="${bar.nombre}">
      <div class="perfil-destacado-info">
        <h3>${bar.nombre}</h3>
        <p><strong>${t("horario")}</strong> ${formatearHorario(bar.opening_hours_weekday_text)}</p>
        <p><strong>${t("tipo")}</strong> ${formatearTipos(bar.types)}</p>
      </div>
    `;

    article.addEventListener("click", function () {
      window.location.href = `bar.html?id=${bar.placeID}`;
    });

    const favoritoBtn = article.querySelector(".favorito-btn");
    favoritoBtn.addEventListener("click", async function (event) {
      event.stopPropagation();

      try {
        const response = await fetch(`${BACKEND_URL}/favoritos`, {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            user_id: Number(usuario.user_id),
            placeID: Number(bar.placeID)
          })
        });

        const data = await response.json();

        if (!response.ok || !data.ok) {
          alert(data.mensaje || t("error_eliminar_favorito"));
          return;
        }

        await pintarFavoritos(usuario, bares);
      } catch (error) {
        console.error("Error eliminando favorito:", error);
        alert(t("error_servidor"));
      }
    });

    perfilDestacadosGrid.appendChild(article);
  });
}

if (opinionesUp && perfilOpinionesList) {
  opinionesUp.addEventListener("click", function () {
    perfilOpinionesList.scrollBy({
      top: -220,
      behavior: "smooth"
    });
  });
}

if (opinionesDown && perfilOpinionesList) {
  opinionesDown.addEventListener("click", function () {
    perfilOpinionesList.scrollBy({
      top: 220,
      behavior: "smooth"
    });
  });
}

async function initPerfil() {
  const usuario = requireLogin();
  if (!usuario) return;

  pintarDatosUsuario(usuario);
  aplicarTraduccionesDOM();

  try {
    const response = await fetch("/data/jaen/json/bares_enriquecidos.json");
    const bares = await response.json();

    await pintarOpinionesUsuario(usuario, bares);
    await pintarFavoritos(usuario, bares);
  } catch (error) {
    console.error("Error cargando perfil:", error);

    if (perfilOpinionesList) {
      perfilOpinionesList.innerHTML = `<p>${t("perfil_error_opiniones")}</p>`;
    }

    if (perfilDestacadosGrid) {
      perfilDestacadosGrid.innerHTML = `<p>${t("perfil_error_favoritos")}</p>`;
    }
  }
}

initPerfil();

document.addEventListener("idiomaCambiado", function () {
  initPerfil();
});