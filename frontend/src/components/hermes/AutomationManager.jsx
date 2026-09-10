import { useState, useEffect } from "react";
import automationService from "../../services/automationService";
import Card from "../common/Card";
import Loading from "../common/Loading";

function AutomationManager() {
  const [automations, setAutomations] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [automationsData, statsData] = await Promise.all([
        automationService.listAutomations(),
        automationService.getStats(),
      ]);
      setAutomations(automationsData.automations || []);
      setStats(statsData);
    } catch (err) {
      console.error("Failed to load automations:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Automation Manager</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <div className="text-center">
            <p className="text-3xl font-bold text-blue-600">{stats?.total || 0}</p>
            <p className="text-sm text-gray-500">Total Automations</p>
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <p className="text-3xl font-bold text-green-600">{stats?.enabled || 0}</p>
            <p className="text-sm text-gray-500">Enabled</p>
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <p className="text-3xl font-bold text-red-600">{stats?.disabled || 0}</p>
            <p className="text-sm text-gray-500">Disabled</p>
          </div>
        </Card>
      </div>

      <Card title="Automations">
        {automations.length === 0 ? (
          <p className="text-gray-500 text-center py-4">No automations configured</p>
        ) : (
          <div className="space-y-2">
            {automations.map((auto) => (
              <div key={auto.id} className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <p className="font-medium">{auto.name}</p>
                  <p className="text-sm text-gray-500">{auto.description}</p>
                </div>
                <span className={`px-2 py-1 text-xs rounded ${
                  auto.enabled ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                }`}>
                  {auto.enabled ? "Enabled" : "Disabled"}
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

export default AutomationManager;
