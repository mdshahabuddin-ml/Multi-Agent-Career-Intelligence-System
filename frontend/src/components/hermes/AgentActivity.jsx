import { useState, useEffect } from "react";
import hermesService from "../../services/hermesService";
import Card from "../common/Card";
import Loading from "../common/Loading";

function AgentActivity() {
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadActivity();
  }, []);

  const loadActivity = async () => {
    try {
      const data = await hermesService.getActivity();
      setActivity(data.activity || []);
    } catch (err) {
      console.error("Failed to load activity:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Loading />;

  return (
    <Card title="Agent Activity">
      {activity.length === 0 ? (
        <p className="text-gray-500 text-center py-4">No recent activity</p>
      ) : (
        <div className="space-y-2">
          {activity.map((item, i) => (
            <div key={i} className="flex items-center gap-3 p-2 border-b">
              <div className="w-2 h-2 bg-blue-500 rounded-full" />
              <div>
                <p className="text-sm font-medium">{item.action}</p>
                <p className="text-xs text-gray-500">{item.timestamp}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export default AgentActivity;
