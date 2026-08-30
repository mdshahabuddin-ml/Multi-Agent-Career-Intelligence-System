import api from "./api";


const researchService = {

    /*
    |--------------------------------------------------------------------------
    | Start Research
    |--------------------------------------------------------------------------
    */

    async startResearch(data) {
        const response = await api.post("/api/research/start", data);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Research Status
    |--------------------------------------------------------------------------
    */

    async getStatus(researchId) {
        const response = await api.get(`/api/research/${researchId}/status`);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Research Report
    |--------------------------------------------------------------------------
    */

    async getReport(researchId) {
        const response = await api.get(`/api/research/${researchId}`);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Cancel Research
    |--------------------------------------------------------------------------
    */

    async cancelResearch(researchId) {
        const response = await api.post(`/api/research/${researchId}/cancel`);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | List Research
    |--------------------------------------------------------------------------
    */

    async listResearch(params = {}) {
        const response = await api.get("/api/research", { params });
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Research Sources
    |--------------------------------------------------------------------------
    */

    async getSources(researchId) {
        const response = await api.get(`/api/research/${researchId}/sources`);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Research Citations
    |--------------------------------------------------------------------------
    */

    async getCitations(researchId) {
        const response = await api.get(`/api/research/${researchId}/citations`);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Research Sources (Alternative)
    |--------------------------------------------------------------------------
    */

    async getResearchSources(researchId) {
        const response = await api.get(`/api/research/${researchId}/sources`);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Research Citations (Alternative)
    |--------------------------------------------------------------------------
    */

    async getResearchCitations(researchId) {
        const response = await api.get(`/api/research/${researchId}/citations`);
        return response.data;
    },

};

export default researchService;