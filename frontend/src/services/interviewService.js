import api from "./api";


const interviewService = {

    /*
    |--------------------------------------------------------------------------
    | Generate Interview Prep
    |--------------------------------------------------------------------------
    */

    async generatePrep(data) {
        const response = await api.post("/api/applications/interview-prep", data);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Interview Questions
    |--------------------------------------------------------------------------
    */

    async getQuestions(data) {
        const response = await api.post("/api/interview/questions", data);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get STAR Stories
    |--------------------------------------------------------------------------
    */

    async getStarStories(data) {
        const response = await api.post("/api/interview/star-stories", data);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Company Research Prompts
    |--------------------------------------------------------------------------
    */

    async getCompanyResearch(data) {
        const response = await api.post("/api/interview/company-research", data);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Technical Preparation
    |--------------------------------------------------------------------------
    */

    async getTechnicalPrep(data) {
        const response = await api.post("/api/interview/technical-prep", data);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Questions to Ask
    |--------------------------------------------------------------------------
    */

    async getQuestionsToAsk(data) {
        const response = await api.post("/api/interview/questions-to-ask", data);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Save Interview Prep
    |--------------------------------------------------------------------------
    */

    async savePrep(data) {
        const response = await api.post("/api/interview/save", data);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Saved Prep
    |--------------------------------------------------------------------------
    */

    async getSavedPrep() {
        const response = await api.get("/api/interview/saved");
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Mock Interview
    |--------------------------------------------------------------------------
    */

    async startMockInterview(data) {
        const response = await api.post("/api/interview/mock/start", data);
        return response.data;
    },

    async submitMockAnswer(data) {
        const response = await api.post("/api/interview/mock/answer", data);
        return response.data;
    },

    async endMockInterview(sessionId) {
        const response = await api.post(`/api/interview/mock/${sessionId}/end`);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Interview Feedback
    |--------------------------------------------------------------------------
    */

    async getFeedback(sessionId) {
        const response = await api.get(`/api/interview/${sessionId}/feedback`);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Self Introduction
    |--------------------------------------------------------------------------
    */

    async getSelfIntro(data) {
        const response = await api.post("/api/interview/self-intro", data);
        return response.data;
    },

};

export default interviewService;