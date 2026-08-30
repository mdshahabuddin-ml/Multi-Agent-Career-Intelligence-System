import api from "./api";


const authService = {

    /*
    |--------------------------------------------------------------------------
    | Register
    |--------------------------------------------------------------------------
    */

    async register(userData) {
        const response =
            await api.post(
                "/api/auth/register",
                userData
            );

        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Login
    |--------------------------------------------------------------------------
    */

    async login(credentials) {
        const response =
            await api.post(
                "/api/auth/login",
                credentials
            );

        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Get Current User
    |--------------------------------------------------------------------------
    */

    async getCurrentUser() {
        const response =
            await api.get(
                "/api/auth/me"
            );

        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Logout
    |--------------------------------------------------------------------------
    */

    logout() {
        localStorage.removeItem(
            "careerintel_token"
        );

        localStorage.removeItem(
            "careerintel_user"
        );
    },


    /*
    |--------------------------------------------------------------------------
    | Token
    |--------------------------------------------------------------------------
    */

    getToken() {
        return localStorage.getItem(
            "careerintel_token"
        );
    },


    /*
    |--------------------------------------------------------------------------
    | Authentication Check
    |--------------------------------------------------------------------------
    */

    isAuthenticated() {
        return Boolean(
            localStorage.getItem(
                "careerintel_token"
            )
        );
    },

};


export default authService;