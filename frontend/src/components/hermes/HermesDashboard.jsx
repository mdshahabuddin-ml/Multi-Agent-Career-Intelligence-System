import { useState, useEffect } from "react";
import hermesService from "../../services/hermesService";
import Card from "../common/Card";
import Loading from "../common/Loading";

function HermesDashboard() {
  const [agents, setAgents] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [agentsData, statsData] = await Promise.all([
        hermesService.listAgents(),
        hermesService.getStats(),
      ]);
      setAgents(agentsData.agents || []);
      setStats(statsData);
    } catch (err) {
      console.error("Failed to load hermes data:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Hermes Dashboard</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <div className="text-center">
            <p className="text-3xl font-bold text-blue-600">{agents.length}</p>
            <p className="text-sm text-gray-500">Active Agents</p>
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <p className="text-3xl font-bold text-green-600">{stats?.tasks_completed || 0}</p>
            <p className="text-sm text-gray-500">Tasks Completed</p>
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <p className="text-3xl font-bold text-purple-600">{stats?.skills || 0}</p>
            <p className="text-sm text-gray-500">Skills Available</p>
          </div>
        </Card>
      </div>

      <Card title="Registered Agents">
        {agents.length === 0 ? (
          <p className="text-gray-500 text-center py-4">No agents registered</p>
        ) : (
          <div className="space-y-2">
            {agents.map((agent) => (
              <div key={agent.agent_id} className="flex items-center justify-between p-2 border rounded">
                <span className="font-medium">{agent.name}</span>
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
    </div>
  );
}

export default HermesDashboard;
