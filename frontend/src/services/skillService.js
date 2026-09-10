import api from "./api";

const skillService = {
  async listSkills(tag = null) {
    const response = await api.get("/api/skills/skills", {
      params: { tag },
    });
    return response.data;
  },

  async getSkill(skillName) {
    const response = await api.get(`/api/skills/skills/${skillName}`);
    return response.data;
  },

  async executeSkill(skillName, params = null, timeout = null) {
    const response = await api.post(`/api/skills/skills/${skillName}/execute`, {
      params,
      timeout,
    });
    return response.data;
  },

  async searchSkills(query) {
    const response = await api.get("/api/skills/skills/search", {
      params: { query },
    });
    return response.data;
  },

  async getStats() {
    const response = await api.get("/api/skills/stats");
    return response.data;
  },
};

export default skillService;
