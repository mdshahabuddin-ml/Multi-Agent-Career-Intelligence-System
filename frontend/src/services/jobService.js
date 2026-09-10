import api from "./api";


const jobService = {

    /*
    |--------------------------------------------------------------------------
    | Search Jobs (POST)
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
    | Get Job
    |--------------------------------------------------------------------------
    */

    async getJob(jobId) {
        const response = await api.get(`/api/jobs/${jobId}`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Job Match
    |--------------------------------------------------------------------------
    */

    async getJobMatch(jobId) {
        const response = await api.get(`/api/jobs/${jobId}/match`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Job Recommendations
    |--------------------------------------------------------------------------
    */

    async getRecommendations(params = {}) {
        const response = await api.get("/api/jobs/recommendations", { params });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Job Stats
    |--------------------------------------------------------------------------
    */

    async getStats() {
        const response = await api.get("/api/jobs/stats");
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
    | Unsave Job
    |--------------------------------------------------------------------------
    */

    async unsaveJob(jobId) {
        const response = await api.delete(`/api/jobs/${jobId}/save`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Saved Jobs
    |--------------------------------------------------------------------------
    */

    async getSavedJobs(signal) {
        const response = await api.get("/api/jobs/saved", { signal });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Job Requirements
    |--------------------------------------------------------------------------
    */

    async getRequirements(jobId) {
        const response = await api.get(`/api/jobs/${jobId}/requirements`);
        return response.data;
    },

};

export default jobService;