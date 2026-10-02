var BACKEND_URL = window.BACKEND_URL || "";

const loginForm = document.getElementById("loginForm");
const togglePassword = document.getElementById("togglePassword");
const passwordInput = document.getElementById("password");
const usernameInput = document.getElementById("username");
const goToRegister = document.getElementById("goToRegister");
const loginError = document.getElementById("loginError");

togglePassword.addEventListener("click", function () {
  const isPassword = passwordInput.type === "password";
  passwordInput.type = isPassword ? "text" : "password";
  togglePassword.textContent = isPassword ? "🙈" : "👁️";
});

goToRegister.addEventListener("click", function () {
  window.location.href = "register.html";
});

loginForm.addEventListener("submit", async function (event) {
  event.preventDefault();

  loginError.textContent = "";

  const username = usernameInput.value.trim();
  const password = passwordInput.value.trim();

  if (username === "" || password === "") {
    loginError.textContent = "Debes introducir nombre de usuario y contraseña.";
    return;
  }

  try {
    const response = await fetch(`${BACKEND_URL}/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        username: username,
        password: password
      })
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
      loginError.textContent = data.mensaje || "Error al iniciar sesión.";
      return;
    }

    localStorage.setItem("usuarioLogueado", JSON.stringify(data.usuario));

    if (!localStorage.getItem("favoritos")) {
      localStorage.setItem("favoritos", JSON.stringify([]));
    }

    window.location.href = "inicio.html";
  } catch (error) {
    console.error("Error en login:", error);
    loginError.textContent = "No se pudo conectar con el servidor.";
  }
});