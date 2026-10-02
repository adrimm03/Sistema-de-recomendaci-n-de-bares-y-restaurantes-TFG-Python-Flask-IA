async function cargarCabecera() {
  const headerContainer = document.getElementById("headerContainer");
  if (!headerContainer) return;

  const response = await fetch("/web/html/cabecera.html");
  const html = await response.text();
  headerContainer.innerHTML = html;

  inicializarCabecera();
  aplicarTraduccionesDOM();
  actualizarBotonesIdioma();
}

function obtenerUsuarioLogueado() {
  const usuario = localStorage.getItem("usuarioLogueado");
  return usuario ? JSON.parse(usuario) : null;
}

function cerrarSesion() {
  localStorage.removeItem("usuarioLogueado");
  window.location.href = "login.html";
}

function actualizarBotonesIdioma() {
  const btnES = document.getElementById("langES");
  const btnEN = document.getElementById("langEN");
  const idioma = obtenerIdiomaActual();

  if (btnES) btnES.classList.toggle("active-lang", idioma === "es");
  if (btnEN) btnEN.classList.toggle("active-lang", idioma === "en");
}

function actualizarBotonPerfil() {
  const profileToggle = document.getElementById("profileToggle");
  const profileDropdown = document.getElementById("profileDropdown");
  const logoutBtn = document.getElementById("logoutBtn");
  const usuario = obtenerUsuarioLogueado();

  if (!profileToggle) return;

  if (usuario) {
    profileToggle.textContent = usuario.username || t("perfil");

    if (profileDropdown) {
      profileDropdown.style.display = "";
    }

    if (logoutBtn) {
      logoutBtn.style.display = "";
    }
  } else {
      profileToggle.textContent = t("iniciar_sesion");

    if (profileDropdown) {
      profileDropdown.classList.remove("show");
    }
  }
}

function inicializarCabecera() {
  const menuToggle = document.getElementById("menuToggle");
  const hamburgerDropdown = document.getElementById("hamburgerDropdown");

  const profileToggle = document.getElementById("profileToggle");
  const profileDropdown = document.getElementById("profileDropdown");

  const logoutBtn = document.getElementById("logoutBtn");
  const btnES = document.getElementById("langES");
  const btnEN = document.getElementById("langEN");

  actualizarBotonPerfil();

  if (menuToggle && hamburgerDropdown && profileDropdown) {
    menuToggle.addEventListener("click", function (event) {
      event.stopPropagation();
      hamburgerDropdown.classList.toggle("show");
      profileDropdown.classList.remove("show");
    });
  }

  if (profileToggle) {
    profileToggle.addEventListener("click", function (event) {
      const usuario = obtenerUsuarioLogueado();

      if (!usuario) {
        event.preventDefault();
        window.location.href = "login.html";
        return;
      }

      event.stopPropagation();

      if (profileDropdown) {
        profileDropdown.classList.toggle("show");
      }

      if (hamburgerDropdown) {
        hamburgerDropdown.classList.remove("show");
      }
    });
  }

  document.addEventListener("click", function () {
    if (hamburgerDropdown) hamburgerDropdown.classList.remove("show");
    if (profileDropdown) profileDropdown.classList.remove("show");
  });

  if (logoutBtn) {
    logoutBtn.addEventListener("click", function (event) {
      event.preventDefault();
      cerrarSesion();
    });
  }

  if (btnES) {
    btnES.addEventListener("click", function () {
      cambiarIdioma("es");
      aplicarTraduccionesDOM();
      actualizarBotonesIdioma();
      actualizarBotonPerfil();
    });
  }

  if (btnEN) {
    btnEN.addEventListener("click", function () {
      cambiarIdioma("en");
      aplicarTraduccionesDOM();
      actualizarBotonesIdioma();
      actualizarBotonPerfil();
    });
  }
}

cargarCabecera();