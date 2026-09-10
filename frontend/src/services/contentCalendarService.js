import api from "./api";

export const contentCalendarService = {
  // CRUD
  create: (data) => api.post("/content-calendar/", data),
  list: (params) => api.get("/content-calendar/", { params }),
  getCalendarView: (startDate, endDate) => 
    api.get("/content-calendar/calendar", { params: { start_date: startDate, end_date: endDate } }),
  getUpcoming: (limit = 10) => api.get("/content-calendar/upcoming", { params: { limit } }),
  get: (id) => api.get(`/content-calendar/${id}`),
  update: (id, data) => api.patch(`/content-calendar/${id}`, data),
  publish: (id) => api.post(`/content-calendar/${id}/publish`),
  schedule: (id, scheduledAt) => api.post(`/content-calendar/${id}/schedule`, null, { params: { scheduled_at: scheduledAt } }),
  delete: (id) => api.delete(`/content-calendar/${id}`),

  // Analytics
  getAnalytics: (contentId) => api.get(`/content-calendar/${contentId}/analytics`),
  getSummary: (params) => api.get("/content-calendar/analytics/summary", { params }),
  syncAnalytics: (contentId, platformPostId, platform, metrics) => 
    api.post("/content-calendar/analytics/sync", {
      content_id: contentId,
      platform_post_id: platformPostId,
      platform,
      metrics
    }),
};

export default contentCalendarService;