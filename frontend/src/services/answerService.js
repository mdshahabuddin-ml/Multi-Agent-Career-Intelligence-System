import api from "./api";


const answerService = {

    /*
    |--------------------------------------------------------------------------
    | Generate Answers
    |--------------------------------------------------------------------------
    */

    async generateAnswers(data) {
        const response = await api.post("/api/applications/answers", data);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Optimize Answer
    |--------------------------------------------------------------------------
    */

    async optimizeAnswer(data) {
        const response = await api.post("/api/applications/answers/optimize", data);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Answer Templates
    |--------------------------------------------------------------------------
    */

    async getTemplates() {
        const response = await api.get("/api/applications/answers/templates");
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Save Answer
    |--------------------------------------------------------------------------
    */

    async saveAnswer(data) {
        const response = await api.post("/api/applications/answers/save", data);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Saved Answers
    |--------------------------------------------------------------------------
    */

    async getSavedAnswers() {
        const response = await api.get("/api/applications/answers/saved");
        return response.data;
    },

};

export default answerService;