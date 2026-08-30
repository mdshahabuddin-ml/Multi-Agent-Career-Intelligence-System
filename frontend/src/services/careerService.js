import api from "./api";


const careerService = {

    /*
    |--------------------------------------------------------------------------
    | Career Assessment
    |--------------------------------------------------------------------------
    */

    async assessCareer(data) {
        const response = await api.post("/api/career/assess", data);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Job Search Strategy
    |--------------------------------------------------------------------------
    */

    async getJobSearchStrategy(targetRole = null) {
        const params = targetRole ? { target_role: targetRole } : {};
        const response = await api.get("/api/career/job-search-strategy", { params });
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Skill Recommendations
    |--------------------------------------------------------------------------
    */

    async getSkillRecommendations(targetRole) {
        const response = await api.get("/api/career/skill-recommendations", {
            params: { target_role: targetRole },
        });
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Career Path Options
    |--------------------------------------------------------------------------
    */

    async getPathOptions(currentRole) {
        const response = await api.get("/api/career/path-options", {
            params: { current_role: currentRole },
        });
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Learning Resources
    |--------------------------------------------------------------------------
    */

    async getLearningResources(skill, difficulty = null, budget = 0) {
        const params = { skill };
        if (difficulty) params.difficulty = difficulty;
        if (budget) params.budget = budget;
        const response = await api.get("/api/career/learning-resources", { params });
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Create Learning Plan
    |--------------------------------------------------------------------------
    */

    async createLearningPlan(data) {
        const response = await api.post("/api/career/learning-plan", data);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Career Insights
    |--------------------------------------------------------------------------
    */

    async getInsights() {
        const response = await api.get("/api/career/insights");
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Create Career Goal
    |--------------------------------------------------------------------------
    */

    async createGoal(data) {
        const response = await api.post("/api/career/goals", data);
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Get Career Goals
    |--------------------------------------------------------------------------
    */

    async getGoals() {
        const response = await api.get("/api/career/goals");
        return response.data;
    },

    /*
    |--------------------------------------------------------------------------
    | Update Goal Progress
    |--------------------------------------------------------------------------
    */

    async updateGoalProgress(goalId, completedMilestones) {
        const response = await api.post(`/api/career/goals/${goalId}/progress`, {
            completed_milestones: completedMilestones,
        });
        return response.data;
    },

};

export default careerService;