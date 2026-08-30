import api from "./api";


const coverLetterService = {

    /*
    |--------------------------------------------------------------------------
    | Generate Cover Letter
    |--------------------------------------------------------------------------
    */

    async generateCoverLetter(data) {
        const response = await api.post("/api/applications/cover-letter", data);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Optimize Cover Letter
    |--------------------------------------------------------------------------
    */

    async optimizeCoverLetter(data) {
        const response = await api.post("/api/applications/cover-letter/optimize", data);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Cover Letter Templates
    |--------------------------------------------------------------------------
    */

    async getTemplates() {
        const response = await api.get("/api/cover-letter/templates");
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Save Cover Letter
    |--------------------------------------------------------------------------
    */

    async saveCoverLetter(data) {
        const response = await api.post("/api/cover-letter/save", data);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Saved Cover Letters
    |--------------------------------------------------------------------------
    */

    async getSavedCoverLetters() {
        const response = await api.get("/api/cover-letter/saved");
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Delete Cover Letter
    |--------------------------------------------------------------------------
    */

    async deleteCoverLetter(coverLetterId) {
        const response = await api.delete(`/api/cover-letter/${coverLetterId}`);
        return response.data;
    },

};

export default coverLetterService;