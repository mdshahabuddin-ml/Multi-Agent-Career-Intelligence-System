import api from "./api";

const hermesService = {
  async listAgents() {
    const response = await api.get("/api/hermes/agents");
    return response.data;
  },

  async getAgent(agentId) {
    const response = await api.get(`/api/hermes/agents/${agentId}`);
    return response.data;
  },

  async executeTask(task, inputData = null, agentId = null) {
    const response = await api.post("/api/hermes/agents/execute", {
      task,
      input_data: inputData,
      agent_id: agentId,
    });
    return response.data;
  },

  async getAgentState(agentId) {
    const response = await api.get(`/api/hermes/agents/${agentId}/state`);
    return response.data;
  },

  async getAgentMemory(agentId, limit = 10) {
    const response = await api.get(`/api/hermes/agents/${agentId}/memory`, {
      params: { limit },
    });
    return response.data;
  },
};

export default hermesService;
