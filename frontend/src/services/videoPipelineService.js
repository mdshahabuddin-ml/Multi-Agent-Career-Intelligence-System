import api from "./api";

const videoPipelineService = {
  async startPipeline(contentId) {
    const response = await api.post("/api/video-pipeline/start", {
      content_id: contentId,
    });
    return response.data;
  },

  async startShortPipeline(contentId) {
    const response = await api.post("/api/video-pipeline/short/start", {
      content_id: contentId,
    });
    return response.data;
  },

  async listPipelines(statusFilter = null, limit = 20) {
    const response = await api.get("/api/video-pipeline/list", {
      params: { status_filter: statusFilter, limit },
    });
    return response.data;
  },

  async listShortPipelines(statusFilter = null, limit = 20) {
    const response = await api.get("/api/video-pipeline/short/list", {
      params: { status_filter: statusFilter, limit },
    });
    return response.data;
  },

  async getPipeline(pipelineId) {
    const response = await api.get(`/api/video-pipeline/${pipelineId}`);
    return response.data;
  },

  async approveVideo(pipelineId) {
    const response = await api.post(`/api/video-pipeline/${pipelineId}/approve`);
    return response.data;
  },

  async rejectVideo(pipelineId, reason = "") {
    const response = await api.post(`/api/video-pipeline/${pipelineId}/reject`, {
      reason,
    });
    return response.data;
  },

  async regenerateVideo(pipelineId) {
    const response = await api.post(`/api/video-pipeline/${pipelineId}/regenerate`);
    return response.data;
  },

  async retryPipeline(pipelineId) {
    const response = await api.post(`/api/video-pipeline/${pipelineId}/retry`);
    return response.data;
  },

  async deletePipeline(pipelineId) {
    const response = await api.delete(`/api/video-pipeline/${pipelineId}`);
    return response.data;
  },
};

export default videoPipelineService;
