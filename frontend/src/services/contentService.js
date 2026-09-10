import api from "./api";

const contentService = {
  async listContent(contentType = null, status = null, limit = 50) {
    const response = await api.get("/api/content/content", {
      params: { content_type: contentType, status, limit },
    });
    return response.data;
  },

  async createContent(title, contentType = "post", body = "", tags = []) {
    const response = await api.post("/api/content/content", {
      title,
      content_type: contentType,
      body,
      tags,
    });
    return response.data;
  },

  async getContent(contentId) {
    const response = await api.get(`/api/content/content/${contentId}`);
    return response.data;
  },

  async updateContent(contentId, updates) {
    const response = await api.put(`/api/content/content/${contentId}`, updates);
    return response.data;
  },

  async deleteContent(contentId) {
    const response = await api.delete(`/api/content/content/${contentId}`);
    return response.data;
  },

  async publishContent(contentId, platforms) {
    const response = await api.post(`/api/content/content/${contentId}/publish`, {
      platforms,
    });
    return response.data;
  },
};

export default contentService;
