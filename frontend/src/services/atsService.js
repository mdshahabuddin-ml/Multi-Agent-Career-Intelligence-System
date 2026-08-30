import api from "./api";


const atsService = {

    /*
    |--------------------------------------------------------------------------
    | ATS Analysis
    |--------------------------------------------------------------------------
    */

    async analyzeResume(resumeText, options = {}) {
        const response = await api.post("/api/applications/ats/analyze", {
            resume_text: resumeText,
            target_role: options.targetRole,
            job_description: options.jobDescription,
        });
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get ATS Score for a Resume
    |--------------------------------------------------------------------------
    */

    async getATSScore(resumeId, options = {}) {
        const params = {};
        if (options.jobId) params.job_id = options.jobId;
        const response = await api.get(`/api/resume/${resumeId}/ats-score`, { params });
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Missing Keywords
    |--------------------------------------------------------------------------
    */

    async getMissingKeywords(resumeId) {
        const response = await api.get(`/api/resume/${resumeId}/missing-keywords`);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Matched Keywords
    |--------------------------------------------------------------------------
    */

    async getMatchedKeywords(resumeId) {
        const response = await api.get(`/api/resume/${resumeId}/matched-keywords`);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get ATS Recommendations
    |--------------------------------------------------------------------------
    */

    async getRecommendations(resumeId) {
        const response = await api.get(`/api/resume/${resumeId}/recommendations`);
        return response.data;
    },

};

export default atsService;