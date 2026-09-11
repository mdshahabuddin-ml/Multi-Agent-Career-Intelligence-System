import api from "./api";

const socialService = {
  async listAccounts() {
    const response = await api.get("/api/social/accounts");
    return response.data;
  },

  async connectAccount(platform, redirectUri = null) {
    const response = await api.post("/api/social/accounts/connect", {
      platform,
      redirect_uri: redirectUri,
    });
    return response.data;
  },

  async completeConnect(platform, code, state, redirectUri = null) {
    const response = await api.post("/api/social/accounts/connect", {
      platform,
      code,
      state,
      redirect_uri: redirectUri,
    });
    return response.data;
  },

  async manualConnectLinkedIn(profileUrl) {
    const response = await api.post("/api/social/accounts/linkedin-manual", {
      profile_url: profileUrl,
    });
    return response.data;
  },

  async manualConnectYouTube(channelUrl) {
    const response = await api.post("/api/social/accounts/youtube-manual", {
      channel_url: channelUrl,
    });
    return response.data;
  },

  async manualConnectGitHub(profileUrl) {
    const response = await api.post("/api/social/accounts/github-manual", {
      profile_url: profileUrl,
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
