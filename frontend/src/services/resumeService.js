import api from "./api";


const resumeService = {

    /*
    |--------------------------------------------------------------------------
    | Upload Resume
    |--------------------------------------------------------------------------
    */

    async uploadResume(file, isPrimary = false) {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("is_primary", isPrimary);

        const response = await api.post("/api/resume/upload", formData, {
            headers: { "Content-Type": "multipart/form-data" },
        });

        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Get Resume
    |--------------------------------------------------------------------------
    */

    async getResume(resumeId) {
        const response = await api.get(`/api/resume/${resumeId}`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Parse Resume
    |--------------------------------------------------------------------------
    */

    async parseResume(resumeId) {
        const response = await api.post(`/api/resume/${resumeId}/parse`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Resume ATS Analysis
    |--------------------------------------------------------------------------
    */

    async analyzeATS(resumeId, targetRole = null, jobDescription = null) {
        const response = await api.post(`/api/resume/${resumeId}/ats`, {
            target_role: targetRole,
            job_description: jobDescription,
        });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Resume Review
    |--------------------------------------------------------------------------
    */

    async reviewResume(resumeId) {
        const response = await api.post(`/api/resume/${resumeId}/review`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Resume ATS Score
    |--------------------------------------------------------------------------
    */

    async getATSScore(resumeId, jobId = null) {
        const params = {};
        if (jobId) params.job_id = jobId;
        const response = await api.get(`/api/resume/${resumeId}/ats-score`, { params });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Resume Review Score
    |--------------------------------------------------------------------------
    */

    async getReviewScore(resumeId) {
        const response = await api.post(`/api/resume/${resumeId}/review`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Resume Versions
    |--------------------------------------------------------------------------
    */

    async getVersions() {
        const response = await api.get("/api/resume/versions");
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Set Primary Resume
    |--------------------------------------------------------------------------
    */

    async setPrimary(resumeId) {
        const response = await api.post(`/api/resume/${resumeId}/primary`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Delete Resume
    |--------------------------------------------------------------------------
    */

    async deleteResume(resumeId) {
        const response = await api.delete(`/api/resume/${resumeId}`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | List Resumes
    |--------------------------------------------------------------------------
    */

    async listResumes() {
        const response = await api.get("/api/resume/");
        return response.data;
    },

};

export default resumeService;