const CONFIG = window.APP_CONFIG || {};

const requiredConfigFields = [
  "cognitoDomain",
  "clientId",
  "redirectUri",
  "apiBaseUrl"
];

const missingConfigFields = requiredConfigFields.filter(
  field => !CONFIG[field] || CONFIG[field].startsWith("YOUR_")
);

const loginButton = document.getElementById("loginButton");
const panelLoginButton = document.getElementById("panelLoginButton");
const logoutButton = document.getElementById("logoutButton");
const refreshButton = document.getElementById("refreshButton");
const signedOutPanel = document.getElementById("signedOutPanel");
const signedInPanel = document.getElementById("signedInPanel");
const assetGrid = document.getElementById("assetGrid");
const assetSummary = document.getElementById("assetSummary");
const message = document.getElementById("message");
const userEmail = document.getElementById("userEmail");

function base64UrlEncode(bytes) {
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

async function sha256(value) {
  return new Uint8Array(
    await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value))
  );
}

function randomVerifier() {
  const bytes = new Uint8Array(64);
  crypto.getRandomValues(bytes);
  return base64UrlEncode(bytes);
}

function parseJwt(token) {
  try {
    const payload = token.split(".")[1]
      .replace(/-/g, "+")
      .replace(/_/g, "/");
    const padded = payload + "=".repeat((4 - payload.length % 4) % 4);
    return JSON.parse(decodeURIComponent(
      atob(padded)
        .split("")
        .map(c => "%" + c.charCodeAt(0).toString(16).padStart(2, "0"))
        .join("")
    ));
  } catch {
    return {};
  }
}

function showMessage(text) {
  message.textContent = text;
  message.classList.remove("hidden");
}

function clearMessage() {
  message.textContent = "";
  message.classList.add("hidden");
}

function getAccessToken() {
  return sessionStorage.getItem("access_token");
}

function getIdToken() {
  return sessionStorage.getItem("id_token");
}

function clearSession() {
  sessionStorage.removeItem("access_token");
  sessionStorage.removeItem("id_token");
  sessionStorage.removeItem("pkce_verifier");
}

function updateUi() {
  const idToken = getIdToken();

  if (!idToken) {
    signedOutPanel.classList.remove("hidden");
    signedInPanel.classList.add("hidden");
    loginButton.classList.remove("hidden");
    logoutButton.classList.add("hidden");
    userEmail.textContent = "";
    return;
  }

  const claims = parseJwt(idToken);
  userEmail.textContent = claims.email || "Signed in";
  signedOutPanel.classList.add("hidden");
  signedInPanel.classList.remove("hidden");
  loginButton.classList.add("hidden");
  logoutButton.classList.remove("hidden");
}

async function login() {
  const verifier = randomVerifier();
  const challenge = base64UrlEncode(await sha256(verifier));

  sessionStorage.setItem("pkce_verifier", verifier);

  const params = new URLSearchParams({
    client_id: CONFIG.clientId,
    response_type: "code",
    scope: "openid email",
    redirect_uri: CONFIG.redirectUri,
    code_challenge_method: "S256",
    code_challenge: challenge
  });

  window.location.href = `${CONFIG.cognitoDomain}/oauth2/authorize?${params.toString()}`;
}

async function exchangeAuthorizationCode(code) {
  const verifier = sessionStorage.getItem("pkce_verifier");

  if (!verifier) {
    throw new Error("PKCE verifier is missing. Start the sign-in process again.");
  }

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: CONFIG.clientId,
    code,
    redirect_uri: CONFIG.redirectUri,
    code_verifier: verifier
  });

  const response = await fetch(`${CONFIG.cognitoDomain}/oauth2/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body
  });

  if (!response.ok) {
    throw new Error(`Cognito token exchange failed (${response.status}).`);
  }

  const tokens = await response.json();

  sessionStorage.setItem("access_token", tokens.access_token);
  sessionStorage.setItem("id_token", tokens.id_token);
  sessionStorage.removeItem("pkce_verifier");

  history.replaceState({}, document.title, CONFIG.redirectUri);
}

async function loadAssets() {
  clearMessage();
  assetSummary.textContent = "Loading assets...";
  assetGrid.innerHTML = "";

  /*
    API Gateway Cognito user-pool authorizers can validate Cognito JWTs.
    We send the ID token because it contains the email and cognito:groups
    claims used by the current Lambda authorization code.
  */
  const token = getIdToken();

  if (!token) {
    updateUi();
    return;
  }

  try {
    const response = await fetch(`${CONFIG.apiBaseUrl}/assets`, {
      method: "GET",
      headers: {
        "Authorization": token
      }
    });

    if (response.status === 401) {
      clearSession();
      updateUi();
      throw new Error("Your login session is no longer valid. Please sign in again.");
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.message || `Asset request failed (${response.status}).`);
    }

    const assets = data.assets || [];
    assetSummary.textContent = `${data.count ?? assets.length} asset(s) assigned to you.`;

    if (assets.length === 0) {
      assetGrid.innerHTML = '<div class="card">No assigned assets were found.</div>';
      return;
    }

    for (const asset of assets) {
      const card = document.createElement("article");
      card.className = "asset-card";

      const title = document.createElement("h3");
      title.textContent = asset.assetTag || asset.assetId || "Asset";

      const details = document.createElement("dl");
      const fields = [
        ["Category", asset.category],
        ["Manufacturer", asset.manufacturer],
        ["Model", asset.model],
        ["Condition", asset.condition],
        ["Status", asset.status],
        ["Department", asset.department],
        ["Room", asset.room]
      ];

      for (const [label, value] of fields) {
        if (value === undefined || value === null || value === "") continue;

        const dt = document.createElement("dt");
        dt.textContent = label;

        const dd = document.createElement("dd");
        dd.textContent = String(value);

        details.append(dt, dd);
      }

      card.append(title, details);
      assetGrid.appendChild(card);
    }
  } catch (error) {
    assetSummary.textContent = "Could not load assets.";
    showMessage(error.message);
  }
}

function logout() {
  clearSession();

  const params = new URLSearchParams({
    client_id: CONFIG.clientId,
    logout_uri: CONFIG.redirectUri
  });

  window.location.href = `${CONFIG.cognitoDomain}/logout?${params.toString()}`;
}

async function start() {
  if (missingConfigFields.length > 0) {
    showMessage(
      `Application configuration is missing: ${missingConfigFields.join(", ")}.`
    );
    return;
  }

  loginButton.addEventListener("click", login);
  panelLoginButton.addEventListener("click", login);
  logoutButton.addEventListener("click", logout);
  refreshButton.addEventListener("click", loadAssets);

  const params = new URLSearchParams(window.location.search);
  const code = params.get("code");
  const error = params.get("error");

  if (error) {
    showMessage(params.get("error_description") || error);
    history.replaceState({}, document.title, CONFIG.redirectUri);
  }

  if (code) {
    try {
      await exchangeAuthorizationCode(code);
    } catch (exchangeError) {
      clearSession();
      showMessage(exchangeError.message);
      history.replaceState({}, document.title, CONFIG.redirectUri);
    }
  }

  updateUi();

  if (getIdToken()) {
    await loadAssets();
  }
}

start();
