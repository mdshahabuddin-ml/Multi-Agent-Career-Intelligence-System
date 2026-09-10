import api from "./api";

const analyticsService = {
  async getMetrics(eventType = null, userId = null, limit = 100) {
    const response = await api.get("/api/analytics/metrics", {
      params: { event_type: eventType, user_id: userId, limit },
    });
    return response.data;
  },

  async recordEvent(eventType, data, userId = null) {
    const response = await api.post("/api/analytics/record", {
      event_type: eventType,
      data,
      user_id: userId,
    });
    return response.data;
  },

  async getStats(userId = null) {
    const response = await api.get("/api/analytics/stats", {
      params: { user_id: userId },
    });
    return response.data;
  },
};

export default analyticsService;
