const traducciones = {
  es: {
    // Cabecera
    logo_title: "Sistema de Recomendación de Bares de Jaén",
    nav_inicio: "Inicio",
    nav_resultados: "Bares recomendados",
    perfil: "Perfil",
    mi_perfil: "Mi perfil",
    favoritos: "Favoritos",
    mis_opiniones: "Mis opiniones",
    cerrar_sesion: "Cerrar sesión",
    contacto: "Contactar con nosotros",
    sobre_app: "Sobre la aplicación",
    ayuda: "Ayuda",
    faq: "Preguntas frecuentes",
    iniciar_sesion: "Iniciar sesión",

    // Inicio
    inicio_title: "Encuentra el bar o restaurante ideal en Jaén",
    inicio_subtitle: "Elige cómo quieres buscar y encuentra locales que encajen contigo.",
    tab_nombre: "Por nombre",
    tab_filtros: "Por filtros",
    tab_descripcion: "Por descripción",

    buscar_nombre_label: "Buscar por nombre:",
    buscar_nombre_placeholder: "Ej.: La Taberna del Centro",
    buscar_nombre_btn: "Buscar por nombre",

    filtro_tipo_label: "Tipo de local:",
    filtro_tipo_todos: "Todos",
    filtro_tipo_bar: "Bar",
    filtro_tipo_restaurante: "Restaurante",
    filtro_tipo_taberna: "Taberna",
    filtro_tipo_cafeteria: "Cafetería",
    filtro_tipo_meson: "Mesón",

    filtro_zona_label: "Zona:",
    filtro_zona_cargando: "Cargando localidades...",

    filtro_precio_label: "Precio:",
    filtro_precio_todos: "Todos",
    filtro_precio_economico: "Económico",
    filtro_precio_medio: "Medio",
    filtro_precio_alto: "Alto",

    aplicar_filtros_btn: "Aplicar filtros",
    limpiar_btn: "Limpiar",

    descripcion_label: "Escribe lo que te apetece:",
    descripcion_placeholder: "Ej.: Me apetece encontrar un bar económico por el centro de Jaén, con buenas tapas, ambiente tranquilo, horario de cena y que tenga platos recomendados como bravas o croquetas.",
    descripcion_helper: "Debes escribir al menos 20 palabras.",
    descripcion_btn: "Buscar recomendación",

    carousel_valorados: "Bares mejor valorados",
    carousel_visitados: "Bares más visitados",

    horario: "Horario:",
    tipo: "Tipo:",
    no_especificado: "No especificado",
    no_disponible: "No disponible",
    login_favoritos: "Debes iniciar sesión para añadir favoritos.",
    error_eliminar_favorito: "No se pudo eliminar el favorito.",
    error_guardar_favorito: "No se pudo guardar el favorito.",
    error_servidor: "No se pudo conectar con el servidor.",
    error_20_palabras: "Debes escribir al menos 20 palabras para describir lo que buscas.",

    // Perfil
    perfil_default_name: "Usuario",
    perfil_sin_email: "Sin email",
    perfil_mis_opiniones: "Mis opiniones",
    perfil_mis_destacados: "Mis destacados",
    perfil_editar_title: "Editar perfil",

    perfil_no_opiniones: "No has publicado opiniones todavía.",
    perfil_no_favoritos: "No tienes bares favoritos todavía.",
    perfil_error_opiniones: "Error cargando opiniones.",
    perfil_error_favoritos: "Error cargando favoritos.",

    quitar_favoritos: "Quitar de favoritos"
  },

  en: {
    // Cabecera
    logo_title: "Jaén Bar Recommendation System",
    nav_inicio: "Home",
    nav_resultados: "Recommended bars",
    perfil: "Profile",
    mi_perfil: "My profile",
    favoritos: "Favorites",
    mis_opiniones: "My reviews",
    cerrar_sesion: "Log out",
    contacto: "Contact us",
    sobre_app: "About the application",
    ayuda: "Help",
    faq: "Frequently asked questions",
    iniciar_sesion: "Log in",

    // Inicio
    inicio_title: "Find the ideal bar or restaurant in Jaén",
    inicio_subtitle: "Choose how you want to search and find places that match your preferences.",
    tab_nombre: "By name",
    tab_filtros: "By filters",
    tab_descripcion: "By description",

    buscar_nombre_label: "Search by name:",
    buscar_nombre_placeholder: "Example: La Taberna del Centro",
    buscar_nombre_btn: "Search by name",

    filtro_tipo_label: "Place type:",
    filtro_tipo_todos: "All",
    filtro_tipo_bar: "Bar",
    filtro_tipo_restaurante: "Restaurant",
    filtro_tipo_taberna: "Tavern",
    filtro_tipo_cafeteria: "Cafeteria",
    filtro_tipo_meson: "Inn",

    filtro_zona_label: "Area:",
    filtro_zona_cargando: "Loading locations...",

    filtro_precio_label: "Price:",
    filtro_precio_todos: "All",
    filtro_precio_economico: "Budget",
    filtro_precio_medio: "Medium",
    filtro_precio_alto: "High",

    aplicar_filtros_btn: "Apply filters",
    limpiar_btn: "Clear",

    descripcion_label: "Write what you feel like:",
    descripcion_placeholder: "Example: I would like to find an affordable bar in central Jaén, with good tapas, a quiet atmosphere, dinner hours, and dishes like patatas bravas or croquettes.",
    descripcion_helper: "You must write at least 20 words.",
    descripcion_btn: "Search recommendation",

    carousel_valorados: "Top rated bars",
    carousel_visitados: "Most visited bars",

    horario: "Schedule:",
    tipo: "Type:",
    no_especificado: "Not specified",
    no_disponible: "Not available",
    login_favoritos: "You must log in to add favorites.",
    error_eliminar_favorito: "Could not remove the favorite.",
    error_guardar_favorito: "Could not save the favorite.",
    error_servidor: "Could not connect to the server.",
    error_20_palabras: "You must write at least 20 words to describe what you are looking for.",

    // Perfil
    perfil_default_name: "User",
    perfil_sin_email: "No email",
    perfil_mis_opiniones: "My reviews",
    perfil_mis_destacados: "My favorites",
    perfil_editar_title: "Edit profile",

    perfil_no_opiniones: "You have not posted any reviews yet.",
    perfil_no_favoritos: "You do not have any favorite bars yet.",
    perfil_error_opiniones: "Error loading reviews.",
    perfil_error_favoritos: "Error loading favorites.",

    quitar_favoritos: "Remove from favorites"
  }
};

function obtenerIdiomaActual() {
  return localStorage.getItem("idioma") || "es";
}

function guardarIdioma(idioma) {
  localStorage.setItem("idioma", idioma);
}

function t(clave) {
  const idioma = obtenerIdiomaActual();
  return traducciones[idioma]?.[clave] || traducciones.es?.[clave] || clave;
}

function aplicarTraduccionesDOM() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const clave = el.dataset.i18n;
    el.textContent = t(clave);
  });

  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const clave = el.dataset.i18nPlaceholder;
    el.setAttribute("placeholder", t(clave));
  });

  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    const clave = el.dataset.i18nTitle;
    el.setAttribute("title", t(clave));
  });
}

function cambiarIdioma(idioma) {
  guardarIdioma(idioma);
  aplicarTraduccionesDOM();
  document.dispatchEvent(new CustomEvent("idiomaCambiado", { detail: { idioma } }));
}