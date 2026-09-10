import { useState, useEffect } from "react";
import hermesService from "../../services/hermesService";
import Card from "../common/Card";
import Loading from "../common/Loading";

function AgentTasks() {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    try {
      const data = await hermesService.listTasks();
      setTasks(data.tasks || []);
    } catch (err) {
      console.error("Failed to load tasks:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Loading />;

  return (
    <Card title="Agent Tasks">
      {tasks.length === 0 ? (
        <p className="text-gray-500 text-center py-4">No tasks found</p>
      ) : (
        <div className="space-y-2">
          {tasks.map((task) => (
            <div key={task.id} className="p-3 border rounded-lg">
              <div className="flex items-center justify-between">
                <span className="font-medium">{task.description}</span>
                <span className={`px-2 py-1 text-xs rounded ${
                  task.status === "completed" ? "bg-green-100 text-green-700" :
                  task.status === "in_progress" ? "bg-yellow-100 text-yellow-700" :
                  "bg-gray-100 text-gray-700"
                }`}>
                  {task.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export default AgentTasks;
