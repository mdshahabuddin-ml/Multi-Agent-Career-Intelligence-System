import api from "./api";

const socialService = {
  async listAccounts() {
    const response = await api.get("/api/social/accounts");
    return response.data;
  },

  async connectAccount(platform, authCode = null) {
    const response = await api.post("/api/social/accounts/connect", {
      platform,
      auth_code: authCode,
    });
    return response.data;
  },

  async disconnectAccount(accountId) {
    const response = await api.delete(`/api/social/accounts/${accountId}`);
    return response.data;
  },

  async listPosts(platform = null, status = null, limit = 50) {
    const response = await api.get("/api/social/posts", {
      params: { platform, status, limit },
    });
    return response.data;
  },

  async createPost(accountId, content, scheduledAt = null) {
    const response = await api.post("/api/social/posts", {
      account_id: accountId,
      content,
      scheduled_at: scheduledAt,
    });
    return response.data;
  },

  async getPost(postId) {
    const response = await api.get(`/api/social/posts/${postId}`);
    return response.data;
  },

  async getQueue() {
    const response = await api.get("/api/social/queue");
    return response.data;
  },
};

export default socialService;
