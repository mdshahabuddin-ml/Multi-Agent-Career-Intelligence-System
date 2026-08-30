import api from "./api";


const applicationService = {

    /*
    |--------------------------------------------------------------------------
    | Prepare Application
    |--------------------------------------------------------------------------
    */

    async prepareApplication(data) {
        const response = await api.post("/api/applications/prepare", data);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Get Applications
    |--------------------------------------------------------------------------
    */

    async getApplications(params = {}) {
        const response = await api.get("/api/applications", { params });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Get Application
    |--------------------------------------------------------------------------
    */

    async getApplication(applicationId) {
        const response = await api.get(`/api/applications/${applicationId}`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Create Application
    |--------------------------------------------------------------------------
    */

    async createApplication(applicationData) {
        const response = await api.post("/api/applications", applicationData);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Update Application
    |--------------------------------------------------------------------------
    */

    async updateApplication(applicationId, applicationData) {
        const response = await api.put(`/api/applications/${applicationId}`, applicationData);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Update Status
    |--------------------------------------------------------------------------
    */

    async updateStatus(applicationId, status) {
        const response = await api.patch(`/api/applications/${applicationId}/status`, { status });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Delete Application
    |--------------------------------------------------------------------------
    */

    async deleteApplication(applicationId) {
        const response = await api.delete(`/api/applications/${applicationId}`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Application Timeline
    |--------------------------------------------------------------------------
    */

    async getTimeline(applicationId) {
        const response = await api.get(`/api/applications/${applicationId}/timeline`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | ATS Analysis
    |--------------------------------------------------------------------------
    */

    async analyzeATS(applicationId, jobDescription = null) {
        const response = await api.post(`/api/applications/${applicationId}/ats`, {
            job_description: jobDescription,
        });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Resume Review
    |--------------------------------------------------------------------------
    */

    async reviewResume(applicationId) {
        const response = await api.post(`/api/applications/${applicationId}/resume/review`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Resume Optimization
    |--------------------------------------------------------------------------
    */

    async optimizeResume(applicationId, jobDescription = null) {
        const response = await api.post(`/api/applications/${applicationId}/resume/optimize`, {
            job_description: jobDescription,
        });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Cover Letter
    |--------------------------------------------------------------------------
    */

    async generateCoverLetter(applicationId, data = {}) {
        const response = await api.post(`/api/applications/${applicationId}/cover-letter`, data);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Cover Letter Optimization
    |--------------------------------------------------------------------------
    */

    async optimizeCoverLetter(applicationId, coverLetter) {
        const response = await api.post(`/api/applications/${applicationId}/cover-letter/optimize`, {
            cover_letter: coverLetter,
        });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Application Answers
    |--------------------------------------------------------------------------
    */

    async generateAnswers(applicationId, questions) {
        const response = await api.post(`/api/applications/${applicationId}/answers`, { questions });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Interview Preparation
    |--------------------------------------------------------------------------
    */

    async prepareInterview(applicationId, jobDescription = null) {
        const response = await api.post(`/api/applications/${applicationId}/interview-prep`, {
            job_description: jobDescription,
        });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Create Application
    |--------------------------------------------------------------------------
    */

    async createApplication(applicationData) {
        const response = await api.post("/api/applications", applicationData);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Update Application
    |--------------------------------------------------------------------------
    */

    async updateApplication(applicationId, applicationData) {
        const response = await api.put(`/api/applications/${applicationId}`, applicationData);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Update Status
    |--------------------------------------------------------------------------
    */

    async updateStatus(applicationId, status) {
        const response = await api.patch(`/api/applications/${applicationId}/status`, { status });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Delete Application
    |--------------------------------------------------------------------------
    */

    async deleteApplication(applicationId) {
        const response = await api.delete(`/api/applications/${applicationId}`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Application Timeline
    |--------------------------------------------------------------------------
    */

    async getTimeline(applicationId) {
        const response = await api.get(`/api/applications/${applicationId}/timeline`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Application Statistics
    |--------------------------------------------------------------------------
    */

    async getStatistics() {
        const response = await api.get("/api/applications/statistics");
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Application Preparation (Full Workflow)
    |--------------------------------------------------------------------------
    */

    async prepareApplication(data) {
        const response = await api.post("/api/applications/prepare", data);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | ATS Analysis
    |--------------------------------------------------------------------------
    */

    async analyzeATS(applicationId, jobDescription = null) {
        const response = await api.post(`/api/applications/${applicationId}/ats`, {
            job_description: jobDescription,
        });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Resume Review
    |--------------------------------------------------------------------------
    */

    async reviewResume(applicationId) {
        const response = await api.post(`/api/applications/${applicationId}/resume/review`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Resume Optimization
    |--------------------------------------------------------------------------
    */

    async optimizeResume(applicationId, jobDescription = null) {
        const response = await api.post(`/api/applications/${applicationId}/resume/optimize`, {
            job_description: jobDescription,
        });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Generate Cover Letter
    |--------------------------------------------------------------------------
    */

    async generateCoverLetter(applicationId, data = {}) {
        const response = await api.post(`/api/applications/${applicationId}/cover-letter`, data);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Cover Letter Optimization
    |--------------------------------------------------------------------------
    */

    async optimizeCoverLetter(applicationId, coverLetter) {
        const response = await api.post(`/api/applications/${applicationId}/cover-letter/optimize`, {
            cover_letter: coverLetter,
        });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Generate Answers
    |--------------------------------------------------------------------------
    */

    async generateAnswers(applicationId, questions) {
        const response = await api.post(`/api/applications/${applicationId}/answers`, { questions });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Interview Preparation
    |--------------------------------------------------------------------------
    */

    async prepareInterview(applicationId, jobDescription = null) {
        const response = await api.post(`/api/applications/${applicationId}/interview-prep`, {
            job_description: jobDescription,
        });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Create Application
    |--------------------------------------------------------------------------
    */

    async createApplication(applicationData) {
        const response = await api.post("/api/applications", applicationData);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Update Application
    |--------------------------------------------------------------------------
    */

    async updateApplication(applicationId, applicationData) {
        const response = await api.put(`/api/applications/${applicationId}`, applicationData);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Update Status
    |--------------------------------------------------------------------------
    */

    async updateStatus(applicationId, status) {
        const response = await api.patch(`/api/applications/${applicationId}/status`, { status });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Delete Application
    |--------------------------------------------------------------------------
    */

    async deleteApplication(applicationId) {
        const response = await api.delete(`/api/applications/${applicationId}`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Application Timeline
    |--------------------------------------------------------------------------
    */

    async getTimeline(applicationId) {
        const response = await api.get(`/api/applications/${applicationId}/timeline`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Application Statistics
    |--------------------------------------------------------------------------
    */

    async getStatistics() {
        const response = await api.get("/api/applications/statistics");
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Application Preparation (Full Workflow)
    |--------------------------------------------------------------------------
    */

    async prepareApplication(data) {
        const response = await api.post("/api/applications/prepare", data);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | ATS Analysis
    |--------------------------------------------------------------------------
    */

    async analyzeATS(applicationId, jobDescription = null) {
        const response = await api.post(`/api/applications/${applicationId}/ats`, {
            job_description: jobDescription,
        });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Resume Review
    |--------------------------------------------------------------------------
    */

    async reviewResume(applicationId) {
        const response = await api.post(`/api/applications/${applicationId}/resume/review`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Resume Optimization
    |--------------------------------------------------------------------------
    */

    async optimizeResume(applicationId, jobDescription = null) {
        const response = await api.post(`/api/applications/${applicationId}/resume/optimize`, {
            job_description: jobDescription,
        });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Generate Cover Letter
    |--------------------------------------------------------------------------
    */

    async generateCoverLetter(applicationId, data = {}) {
        const response = await api.post(`/api/applications/${applicationId}/cover-letter`, data);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Cover Letter Optimization
    |--------------------------------------------------------------------------
    */

    async optimizeCoverLetter(applicationId, coverLetter) {
        const response = await api.post(`/api/applications/${applicationId}/cover-letter/optimize`, {
            cover_letter: coverLetter,
        });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Generate Answers
    |--------------------------------------------------------------------------
    */

    async generateAnswers(applicationId, questions) {
        const response = await api.post(`/api/applications/${applicationId}/answers`, { questions });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Interview Preparation
    |--------------------------------------------------------------------------
    */

    async prepareInterview(applicationId, jobDescription = null) {
        const response = await api.post(`/api/applications/${applicationId}/interview-prep`, {
            job_description: jobDescription,
        });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Create Application
    |--------------------------------------------------------------------------
    */

    async createApplication(applicationData) {
        const response = await api.post("/api/applications", applicationData);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Update Application
    |--------------------------------------------------------------------------
    */

    async updateApplication(applicationId, applicationData) {
        const response = await api.put(`/api/applications/${applicationId}`, applicationData);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Update Status
    |--------------------------------------------------------------------------
    */

    async updateStatus(applicationId, status) {
        const response = await api.patch(`/api/applications/${applicationId}/status`, { status });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Delete Application
    |--------------------------------------------------------------------------
    */

    async deleteApplication(applicationId) {
        const response = await api.delete(`/api/applications/${applicationId}`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Application Timeline
    |--------------------------------------------------------------------------
    */

    async getTimeline(applicationId) {
        const response = await api.get(`/api/applications/${applicationId}/timeline`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Application Statistics
    |--------------------------------------------------------------------------
    */

    async getStatistics() {
        const response = await api.get("/api/applications/statistics");
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Application Preparation (Full Workflow)
    |--------------------------------------------------------------------------
    */

    async prepareApplication(data) {
        const response = await api.post("/api/applications/prepare", data);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | ATS Analysis
    |--------------------------------------------------------------------------
    */

    async analyzeATS(applicationId, jobDescription = null) {
        const response = await api.post(`/api/applications/${applicationId}/ats`, {
            job_description: jobDescription,
        });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Resume Review
    |--------------------------------------------------------------------------
    */

    async reviewResume(applicationId) {
        const response = await api.post(`/api/applications/${applicationId}/resume/review`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Resume Optimization
    |--------------------------------------------------------------------------
    */

    async optimizeResume(applicationId, jobDescription = null) {
        const response = await api.post(`/api/applications/${applicationId}/resume/optimize`, {
            job_description: jobDescription,
        });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Generate Cover Letter
    |--------------------------------------------------------------------------
    */

    async generateCoverLetter(applicationId, data = {}) {
        const response = await api.post(`/api/applications/${applicationId}/cover-letter`, data);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Cover Letter Optimization
    |--------------------------------------------------------------------------
    */

    async optimizeCoverLetter(applicationId, coverLetter) {
        const response = await api.post(`/api/applications/${applicationId}/cover-letter/optimize`, {
            cover_letter: coverLetter,
        });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Generate Answers
    |--------------------------------------------------------------------------
    */

    async generateAnswers(applicationId, questions) {
        const response = await api.post(`/api/applications/${applicationId}/answers`, { questions });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Interview Preparation
    |--------------------------------------------------------------------------
    */

    async prepareInterview(applicationId, jobDescription = null) {
        const response = await api.post(`/api/applications/${applicationId}/interview-prep`, {
            job_description: jobDescription,
        });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Create Application
    |--------------------------------------------------------------------------
    */

    async createApplication(applicationData) {
        const response = await api.post("/api/applications", applicationData);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Update Application
    |--------------------------------------------------------------------------
    */

    async updateApplication(applicationId, applicationData) {
        const response = await api.put(`/api/applications/${applicationId}`, applicationData);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Update Status
    |--------------------------------------------------------------------------
    */

    async updateStatus(applicationId, status) {
        const response = await api.patch(`/api/applications/${applicationId}/status`, { status });
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Delete Application
    |--------------------------------------------------------------------------
    */

    async deleteApplication(applicationId) {
        const response = await api.delete(`/api/applications/${applicationId}`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Application Timeline
    |--------------------------------------------------------------------------
    */

    async getTimeline(applicationId) {
        const response = await api.get(`/api/applications/${applicationId}/timeline`);
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Application Statistics
    |--------------------------------------------------------------------------
    */

    async getStatistics() {
        const response = await api.get("/api/applications/statistics");
        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Application Preparation (Full Workflow)
    |--------------------------------------------------------------------------
    */

    async prepareApplication(data) {
        const response = await api.post("/api/applications/prepare", data);
        return response.data;
    },

};

export default applicationService;