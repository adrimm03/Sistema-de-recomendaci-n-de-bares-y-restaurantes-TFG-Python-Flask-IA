var BACKEND_URL = window.BACKEND_URL || "";

const registerForm = document.getElementById("registerForm");

const nameInput = document.getElementById("name");
const emailInput = document.getElementById("email");
const countryInput = document.getElementById("country");
const cityInput = document.getElementById("city");
const birthdateInput = document.getElementById("birthdate");
const passwordInput = document.getElementById("password");
const repeatPasswordInput = document.getElementById("repeatPassword");

const nameError = document.getElementById("nameError");
const emailError = document.getElementById("emailError");
const countryError = document.getElementById("countryError");
const cityError = document.getElementById("cityError");
const birthdateError = document.getElementById("birthdateError");
const passwordError = document.getElementById("passwordError");
const repeatPasswordError = document.getElementById("repeatPasswordError");
const registerError = document.getElementById("registerError");

const togglePassword = document.getElementById("togglePassword");
const toggleRepeatPassword = document.getElementById("toggleRepeatPassword");
const backToLogin = document.getElementById("backToLogin");

function clearErrors() {
  nameError.textContent = "";
  emailError.textContent = "";
  countryError.textContent = "";
  cityError.textContent = "";
  birthdateError.textContent = "";
  passwordError.textContent = "";
  repeatPasswordError.textContent = "";
  registerError.textContent = "";
}

function validateEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

function toggleVisibility(input, toggleElement) {
  const isPassword = input.type === "password";
  input.type = isPassword ? "text" : "password";
  toggleElement.textContent = isPassword ? "🙈" : "👁️";
}

togglePassword.addEventListener("click", function () {
  toggleVisibility(passwordInput, togglePassword);
});

toggleRepeatPassword.addEventListener("click", function () {
  toggleVisibility(repeatPasswordInput, toggleRepeatPassword);
});

backToLogin.addEventListener("click", function () {
  window.location.href = "login.html";
});

registerForm.addEventListener("submit", async function (event) {
  event.preventDefault();
  clearErrors();

  let isValid = true;

  const nameValue = nameInput.value.trim();
  const emailValue = emailInput.value.trim();
  const countryValue = countryInput.value;
  const cityValue = cityInput.value.trim();
  const birthdateValue = birthdateInput.value;
  const passwordValue = passwordInput.value;
  const repeatPasswordValue = repeatPasswordInput.value;

  if (nameValue === "") {
    nameError.textContent = "El nombre de usuario es obligatorio.";
    isValid = false;
  }

  if (emailValue === "") {
    emailError.textContent = "El email es obligatorio.";
    isValid = false;
  } else if (!validateEmail(emailValue)) {
    emailError.textContent = "Introduce un email válido, por ejemplo: usuario@correo.com";
    isValid = false;
  }

  if (countryValue === "") {
    countryError.textContent = "Debes seleccionar un país.";
    isValid = false;
  }

  if (cityValue === "") {
    cityError.textContent = "La ciudad es obligatoria.";
    isValid = false;
  }

  if (birthdateValue === "") {
    birthdateError.textContent = "Debes indicar tu fecha de nacimiento.";
    isValid = false;
  }

  if (passwordValue === "") {
    passwordError.textContent = "La contraseña es obligatoria.";
    isValid = false;
  } else if (passwordValue.length < 6) {
    passwordError.textContent = "La contraseña debe tener al menos 6 caracteres.";
    isValid = false;
  }

  if (repeatPasswordValue === "") {
    repeatPasswordError.textContent = "Debes repetir la contraseña.";
    isValid = false;
  } else if (passwordValue !== repeatPasswordValue) {
    repeatPasswordError.textContent = "Las contraseñas no coinciden.";
    isValid = false;
  }

  if (!isValid) {
    return;
  }

  try {
    const response = await fetch(`${BACKEND_URL}/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        username: nameValue,
        email: emailValue,
        password: passwordValue,
        fecha_nacimiento: birthdateValue
      })
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
      registerError.textContent = data.mensaje || "No se pudo registrar el usuario.";
      return;
    }

    alert("Usuario registrado correctamente. Ahora puedes iniciar sesión.");
    window.location.href = "login.html";
  } catch (error) {
    console.error("Error en register:", error);
    registerError.textContent = "No se pudo conectar con el servidor.";
  }
});