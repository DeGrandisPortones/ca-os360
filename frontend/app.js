const TOKEN_KEY = "dflex_auth_token";

const loginCard = document.getElementById("login-card");
const appCard = document.getElementById("app-card");
const loginForm = document.getElementById("login-form");
const transformForm = document.getElementById("transform-form");
const loginMessage = document.getElementById("login-message");
const transformMessage = document.getElementById("transform-message");
const logoutBtn = document.getElementById("logout-btn");
const submitBtn = document.getElementById("submit-btn");

function getToken() {
  return window.localStorage.getItem(TOKEN_KEY) || "";
}

function setToken(token) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

function showLoggedInState() {
  loginCard.classList.add("hidden");
  appCard.classList.remove("hidden");
  loginMessage.textContent = "";
}

function showLoggedOutState() {
  appCard.classList.add("hidden");
  loginCard.classList.remove("hidden");
  transformMessage.textContent = "";
}

function setMessage(element, text, isError = false) {
  element.textContent = text;
  element.classList.toggle("error", isError);
  element.classList.toggle("success", !isError && text !== "");
}

async function parseError(response) {
  try {
    const data = await response.json();
    return data.error || "Ocurrió un error inesperado.";
  } catch (error) {
    return "Ocurrió un error inesperado.";
  }
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(loginForm);
  const username = String(formData.get("username") || "").trim();
  const password = String(formData.get("password") || "");

  setMessage(loginMessage, "Validando acceso...");

  try {
    const response = await fetch("/api/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ username, password })
    });

    if (!response.ok) {
      setMessage(loginMessage, await parseError(response), true);
      return;
    }

    const data = await response.json();
    setToken(data.token);
    loginForm.reset();
    showLoggedInState();
    setMessage(transformMessage, "Sesión iniciada.");
  } catch (error) {
    setMessage(loginMessage, "No se pudo conectar con el servidor.", true);
  }
});

transformForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const token = getToken();
  if (!token) {
    showLoggedOutState();
    setMessage(loginMessage, "Tu sesión no está activa.", true);
    return;
  }

  const fileInput = transformForm.querySelector('input[name="file"]');
  const file = fileInput.files?.[0];
  if (!file) {
    setMessage(transformMessage, "Elegí un archivo antes de continuar.", true);
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  submitBtn.disabled = true;
  setMessage(transformMessage, "Procesando archivo...");

  try {
    const response = await fetch("/api/transform", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`
      },
      body: formData
    });

    if (!response.ok) {
      const message = await parseError(response);
      if (response.status === 401) {
        clearToken();
        showLoggedOutState();
        setMessage(loginMessage, message, true);
        return;
      }
      setMessage(transformMessage, message, true);
      return;
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "Lista de import.xlsx";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);

    transformForm.reset();
    setMessage(transformMessage, "Archivo generado correctamente.");
  } catch (error) {
    setMessage(transformMessage, "No se pudo conectar con el servidor.", true);
  } finally {
    submitBtn.disabled = false;
  }
});

logoutBtn.addEventListener("click", () => {
  clearToken();
  transformForm.reset();
  showLoggedOutState();
  setMessage(loginMessage, "Sesión cerrada.");
});

if (getToken()) {
  showLoggedInState();
} else {
  showLoggedOutState();
}
