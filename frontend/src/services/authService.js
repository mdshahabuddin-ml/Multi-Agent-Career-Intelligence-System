import api from "./api";

const authService = {

    async register(userData) {
        const response = await api.post("/api/auth/register", userData);
        return response.data;
    },

    async login(credentials) {
        const response = await api.post("/api/auth/login", credentials);
        return response.data;
    },

    async getCurrentUser() {
        const response = await api.get("/api/auth/me");
        return response.data;
    },

    // Same as getCurrentUser but bypasses the api.js GET response cache,
    // so session validation always hits the backend (a cached 200 could
    // mask an expired token).
    async getCurrentUserFresh() {
        const response = await api.request({ method: "get", url: "/api/auth/me" });
        return response.data;
    },

    logout() {
        localStorage.removeItem("careerintel_token");
        localStorage.removeItem("careerintel_user");
    },

    getToken() {
        return localStorage.getItem("careerintel_token");
    },

    isAuthenticated() {
        return Boolean(localStorage.getItem("careerintel_token"));
    },
};

export default authService;