import { useState, useEffect } from "react";
import hermesService from "../../services/hermesService";
import Card from "../common/Card";
import Loading from "../common/Loading";

function SubAgents() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    try {
      const data = await hermesService.listAgents();
      setAgents(data.agents || []);
    } catch (err) {
      console.error("Failed to load agents:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Loading />;

  return (
    <Card title="Sub-Agents">
      {agents.length === 0 ? (
        <p className="text-gray-500 text-center py-4">No sub-agents registered</p>
      ) : (
        <div className="space-y-2">
          {agents.map((agent) => (
            <div key={agent.agent_id} className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <p className="font-medium">{agent.name}</p>
                <p className="text-sm text-gray-500">ID: {agent.agent_id}</p>
              </div>
              <span className={`px-2 py-1 text-xs rounded ${
                agent.state === "idle" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"
              }`}>
                {agent.state}
              </span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export default SubAgents;
