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

      <div className="hermes-stat-row">
        <div className="hermes-stat-card">
          <div className="hermes-stat-top">
            <span className="hermes-stat-icon blue" aria-hidden="true">◉</span>
            <span className="hermes-stat-label">Active Agents</span>
          </div>
          <p className="hermes-stat-value">{agents.length}</p>
          <p className="hermes-stat-sub">Currently active</p>
        </div>
        <div className="hermes-stat-card">
          <div className="hermes-stat-top">
            <span className="hermes-stat-icon green" aria-hidden="true">✓</span>
            <span className="hermes-stat-label">Tasks Completed</span>
          </div>
          <p className="hermes-stat-value">{stats?.tasks_completed || 0}</p>
          <p className="hermes-stat-sub">Successfully completed</p>
        </div>
        <div className="hermes-stat-card">
          <div className="hermes-stat-top">
            <span className="hermes-stat-icon purple" aria-hidden="true">✦</span>
            <span className="hermes-stat-label">Skills Available</span>
          </div>
          <p className="hermes-stat-value">{stats?.skills || 0}</p>
          <p className="hermes-stat-sub">Registered capabilities</p>
        </div>
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
