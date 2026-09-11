import api from "./api";

const publishingService = {
  async publishToYouTube({
    contentId,
    title,
    description = "",
    videoUrl = null,
    tags = [],
    privacy = "unlisted",
    categoryId = "27",
  }) {
    const response = await api.post("/api/publishing/youtube", {
      content_id: contentId,
      title,
      description,
      video_url: videoUrl,
      tags,
      privacy,
      category_id: categoryId,
    });
    return response.data;
  },

  async getPublishStatus(contentId) {
    const response = await api.get(`/api/publishing/youtube/status/${contentId}`);
    return response.data;
  },

  async getPublishQueue() {
    const response = await api.get("/api/publishing/youtube/queue");
    return response.data;
  },
};

export default publishingService;
