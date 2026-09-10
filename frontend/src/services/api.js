import axios from "axios";

const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL ||
    "";

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,

    // IMPORTANT:
    // Allows the browser to send/receive the CSRF cookie
    // between frontend (5173) and backend (8080).
    withCredentials: true,

    headers: {
        "Content-Type": "application/json",
    },
});

/*
|--------------------------------------------------------------------------
| Request Deduplication & Response Cache
|--------------------------------------------------------------------------
| Prevents duplicate in-flight GET requests (e.g. from React StrictMode
| double-mount or multiple components requesting the same data).
| Cached responses are reused for 30 seconds to avoid redundant server
| calls when navigating back to the same page or remounting components.
*/

const _getResponseCache = new Map();
const _inflightGetCache = new Map();
const GET_CACHE_TTL = 30000;

const _originalGet = api.get.bind(api);

api.get = function dedupedGet(url, config = {}) {
    const cacheKey = `${url}:${JSON.stringify(config.params || {})}`;

    // 1. Serve from response cache if still valid
    const cached = _getResponseCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < GET_CACHE_TTL) {
        return Promise.resolve(cached.response);
    }

    // 2. If the same request is already in-flight, return the shared promise
    if (_inflightGetCache.has(cacheKey)) {
        return _inflightGetCache.get(cacheKey);
    }

    // 3. Strip the AbortController signal so individual component unmounts
    //    (e.g. React StrictMode cleanup) do NOT abort the shared request.
    const { signal: _signal, ...restConfig } = config;

    const promise = _originalGet(url, restConfig)
        .then((response) => {
            _getResponseCache.set(cacheKey, {
                response,
                timestamp: Date.now(),
            });
            return response;
        })
        .finally(() => {
            // Keep the in-flight entry briefly so the StrictMode remount
            // (same synchronous tick) can still find it.
            setTimeout(() => _inflightGetCache.delete(cacheKey), 100);
        });

    _inflightGetCache.set(cacheKey, promise);
    return promise;
};

/*
|--------------------------------------------------------------------------
| CSRF Token
|--------------------------------------------------------------------------
*/

const CSRF_COOKIE_NAME = "csrf_token";
const CSRF_HEADER_NAME = "X-CSRF-Token";

function getCookie(name) {
    const cookies = document.cookie ? document.cookie.split("; ") : [];

    for (const cookie of cookies) {
        const [key, ...valueParts] = cookie.split("=");

        if (key === name) {
            return decodeURIComponent(valueParts.join("="));
        }
    }

    return null;
}

let csrfTokenPromise = null;

// Single-flight session verification: when a protected endpoint rejects
// our token with 401, confirm once against the canonical "am I logged in?"
// endpoint instead of trusting a single (possibly transient) failure.
// Uses api.request (NOT the deduped api.get) to bypass the GET cache.
let authVerifyPromise = null;

function verifySession() {
    if (!authVerifyPromise) {
        authVerifyPromise = api
            .request({ method: "get", url: "/api/auth/me" })
            .finally(() => {
                authVerifyPromise = null;
            });
    }
    return authVerifyPromise;
}

/*
|--------------------------------------------------------------------------
| Auth Cache / Session Helpers
|--------------------------------------------------------------------------
| Central place to wipe client-side auth state when the backend has told
| us the stored JWT is genuinely invalid (expired, revoked, or signed
| with an unknown key). This preserves security: we never bypass or
| weaken JWT/CSRF checks, we just stop sending a dead token and send
| the user back to /login for a fresh one.
*/

export function clearApiCache() {
    _getResponseCache.clear();
    _inflightGetCache.clear();
    csrfTokenPromise = null;
    authVerifyPromise = null;
}

export function hardLogout() {
    localStorage.removeItem("careerintel_token");
    localStorage.removeItem("careerintel_user");
    clearApiCache();
    if (
        typeof window !== "undefined" &&
        window.location?.pathname !== "/login"
    ) {
        window.location.href = "/login";
    }
}

async function ensureCsrfToken() {
    if (csrfTokenPromise) {
        return csrfTokenPromise;
    }

    csrfTokenPromise = (async () => {
        let token = getCookie(CSRF_COOKIE_NAME);

        if (token) {
            return token;
        }

        const response = await api.get("/api/security/csrf-token");

        token = response.data?.csrf_token;

        if (!token) {
            throw new Error("CSRF token was not returned by the server.");
        }

        return token;
    })();

    return csrfTokenPromise;
}

/*
|--------------------------------------------------------------------------
| Request Interceptor
|--------------------------------------------------------------------------
| Automatically attach JWT token and CSRF token when authenticated.
*/

api.interceptors.request.use(
    async (config) => {
        const token = localStorage.getItem("careerintel_token");

        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }

        // Attach CSRF token for mutating requests
        const mutatingMethods = ["post", "put", "patch", "delete"];
        if (mutatingMethods.includes(config.method?.toLowerCase())) {
            try {
                const csrfToken = await ensureCsrfToken();
                if (csrfToken) {
                    config.headers[CSRF_HEADER_NAME] = csrfToken;
                }
            } catch (err) {
                console.warn("Failed to get CSRF token:", err);
            }
        }

        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

/*
|--------------------------------------------------------------------------
| Response Interceptor
|--------------------------------------------------------------------------
*/

api.interceptors.response.use(
    (response) => {
        // Invalidate GET response cache when a mutation succeeds
        // so subsequent GETs fetch fresh data.
        const method = response.config?.method?.toLowerCase();
        if (["post", "put", "patch", "delete"].includes(method)) {
            const mutationUrl = response.config?.url || "";
            for (const key of _getResponseCache.keys()) {
                if (key.startsWith(mutationUrl)) {
                    _getResponseCache.delete(key);
                }
            }
        }

        return response;
    },

    (error) => {
        if (error.response?.status === 401) {
            const url = error.config?.url || "";
            const isAuthCheck = url.includes("/api/auth/me");
            const isLogin = url.includes("/api/auth/login");

            // Never react to the login endpoint itself rejecting credentials.
            if (isLogin) {
                return Promise.reject(error);
            }

            // The canonical session check rejected us: the stored JWT is
            // genuinely invalid (expired, revoked, unknown key, user gone).
            // Wipe it and go back to /login for a fresh token.
            if (isAuthCheck) {
                hardLogout();
                return Promise.reject(error);
            }

            // Any other protected endpoint rejected the token. It may be
            // transient, so verify once against /api/auth/me (single-flight
            // so N failing widgets trigger only ONE check). If the check
            // also 401s, its own interceptor path above logs us out.
            // Network failures (no response) resolve here as rejection
            // without logout — we only log out on confirmed 401s.
            return verifySession().then(
                () => Promise.reject(error),
                (verifyError) => {
                    if (!verifyError?.response) {
                        return Promise.reject(error);
                    }
                    return Promise.reject(error);
                }
            );
        }

        // Handle CSRF token expiry
        if (error.response?.status === 403 && error.response?.data?.detail?.includes("CSRF")) {
            csrfTokenPromise = null; // Force token refresh on next request
        }

        return Promise.reject(error);
    }
);

export default api;