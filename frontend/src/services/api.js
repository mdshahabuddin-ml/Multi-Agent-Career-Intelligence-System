import axios from "axios";

const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL ||
    "http://localhost:8000";


const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,

    headers: {
        "Content-Type": "application/json",
    },
});


/*
|--------------------------------------------------------------------------
| Request Interceptor
|--------------------------------------------------------------------------
| Automatically attach JWT token when the user is authenticated.
*/

api.interceptors.request.use(
    (config) => {
        const token =
            localStorage.getItem("careerintel_token");

        if (token) {
            config.headers.Authorization =
                `Bearer ${token}`;
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
        return response;
    },

    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem(
                "careerintel_token"
            );

            localStorage.removeItem(
                "careerintel_user"
            );
        }

        return Promise.reject(error);
    }
);


export default api;