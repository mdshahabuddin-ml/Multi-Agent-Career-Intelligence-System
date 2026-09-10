import api from "./api";

const automationService = {
  async listAutomations() {
    const response = await api.get("/api/automations/automations");
    return response.data;
  },

  async createAutomation(name, description = "", schedule = null) {
    const response = await api.post("/api/automations/automations", {
      name,
      description,
      schedule,
    });
    return response.data;
  },

  async getAutomation(automationId) {
    const response = await api.get(`/api/automations/automations/${automationId}`);
    return response.data;
  },

  async executeAutomation(automationId, data = null) {
    const response = await api.post(`/api/automations/automations/${automationId}/execute`, data);
    return response.data;
  },

  async enableAutomation(automationId) {
    const response = await api.put(`/api/automations/automations/${automationId}/enable`);
    return response.data;
  },

  async disableAutomation(automationId) {
    const response = await api.put(`/api/automations/automations/${automationId}/disable`);
    return response.data;
  },

  async getStats() {
    const response = await api.get("/api/automations/stats");
    return response.data;
  },

  async getScheduled() {
    const response = await api.get("/api/automations/scheduled");
    return response.data;
  },
};

export default automationService;
