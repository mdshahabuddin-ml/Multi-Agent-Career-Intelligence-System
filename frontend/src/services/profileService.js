import api from "./api";


const profileService = {

    /*
    |--------------------------------------------------------------------------
    | Get Profile
    |--------------------------------------------------------------------------
    */

    async getProfile() {
        const response =
            await api.get(
                "/api/profile"
            );

        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Create Profile
    |--------------------------------------------------------------------------
    */

    async createProfile(profileData) {
        const response =
            await api.post(
                "/api/profile",
                profileData
            );

        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Update Profile
    |--------------------------------------------------------------------------
    */

    async updateProfile(profileData) {
        const response =
            await api.put(
                "/api/profile",
                profileData
            );

        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Skills
    |--------------------------------------------------------------------------
    */

    async getSkills() {
        const response =
            await api.get(
                "/api/profile/skills"
            );

        return response.data;
    },


    async addSkill(skillData) {
        const response =
            await api.post(
                "/api/profile/skills",
                skillData
            );

        return response.data;
    },


    async deleteSkill(skillId) {
        const response =
            await api.delete(
                `/api/profile/skills/${skillId}`
            );

        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Projects
    |--------------------------------------------------------------------------
    */

    async getProjects() {
        const response =
            await api.get(
                "/api/profile/projects"
            );

        return response.data;
    },


    async addProject(projectData) {
        const response =
            await api.post(
                "/api/profile/projects",
                projectData
            );

        return response.data;
    },


    async updateProject(
        projectId,
        projectData
    ) {
        const response =
            await api.put(
                `/api/profile/projects/${projectId}`,
                projectData
            );

        return response.data;
    },


    async deleteProject(projectId) {
        const response =
            await api.delete(
                `/api/profile/projects/${projectId}`
            );

        return response.data;
    },


    /*
    |--------------------------------------------------------------------------
    | Experience
    |--------------------------------------------------------------------------
    */

    async getExperience() {
        const response =
            await api.get(
                "/api/profile/experience"
            );

        return response.data;
    },


    async addExperience(
        experienceData
    ) {
        const response =
            await api.post(
                "/api/profile/experience",
                experienceData
            );

        return response.data;
    },


    async updateExperience(
        experienceId,
        experienceData
    ) {
        const response =
            await api.put(
                `/api/profile/experience/${experienceId}`,
                experienceData
            );

        return response.data;
    },


    async deleteExperience(
        experienceId
    ) {
        const response =
            await api.delete(
                `/api/profile/experience/${experienceId}`
            );

        return response.data;
    },

};


export default profileService;