import api from "./api";


const jobSearchService = {

    /*
    |--------------------------------------------------------------------------
    | Search Jobs
    |--------------------------------------------------------------------------
    */

    async searchJobs(params = {}) {
        const response = await api.post("/api/jobs/search", params);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Search Jobs (GET)
    |--------------------------------------------------------------------------
    */

    async searchJobsGet(params = {}) {
        const response = await api.get("/api/jobs/search", { params });
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Job Recommendations
    |--------------------------------------------------------------------------
    */

    async getRecommendations(params = {}) {
        const response = await api.get("/api/jobs/recommendations", { params });
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Job Stats
    |--------------------------------------------------------------------------
    */

    async getStats() {
        const response = await api.get("/api/jobs/stats");
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Job Details
    |--------------------------------------------------------------------------
    */

    async getJob(jobId) {
        const response = await api.get(`/api/jobs/${jobId}`);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Save Job
    |--------------------------------------------------------------------------
    */

    async saveJob(jobId, notes = null) {
        const response = await api.post(`/api/jobs/${jobId}/save`, { notes });
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Saved Jobs
    |--------------------------------------------------------------------------
    */

    async getSavedJobs() {
        const response = await api.get("/api/jobs/saved");
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Job Requirements
    |--------------------------------------------------------------------------
    */

    async getRequirements(jobId) {
        const response = await api.get(`/api/jobs/${jobId}/requirements`);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Job Match
    |--------------------------------------------------------------------------
    */

    async getJobMatch(jobId) {
        const response = await api.get(`/api/jobs/${jobId}/match`);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Job Stats
    |--------------------------------------------------------------------------
    */

    async getJobStats() {
        const response = await api.get("/api/jobs/stats");
        return response.data;
    },

};

export default jobSearchService;