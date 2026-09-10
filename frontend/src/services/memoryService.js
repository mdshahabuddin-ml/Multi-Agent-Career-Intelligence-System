import api from "./api";

const memoryService = {
  async listMemories(category = null, limit = 50) {
    const response = await api.get("/api/memory/memories", {
      params: { category, limit },
    });
    return response.data;
  },

  async storeMemory(content, category = "general", metadata = null) {
    const response = await api.post("/api/memory/memories", {
      content,
      category,
      metadata,
    });
    return response.data;
  },

  async deleteMemory(memoryId) {
    const response = await api.delete(`/api/memory/memories/${memoryId}`);
    return response.data;
  },

  async searchMemories(query, category = null, limit = 10) {
    const response = await api.get("/api/memory/memories/search", {
      params: { query, category, limit },
    });
    return response.data;
  },

  async getStats() {
    const response = await api.get("/api/memory/memories/stats");
    return response.data;
  },
};

export default memoryService;
