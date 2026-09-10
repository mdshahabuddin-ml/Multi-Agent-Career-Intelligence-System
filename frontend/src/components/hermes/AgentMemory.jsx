import { useState, useEffect } from "react";
import memoryService from "../../services/memoryService";
import Card from "../common/Card";
import Loading from "../common/Loading";

function AgentMemory() {
  const [memories, setMemories] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [memoriesData, statsData] = await Promise.all([
        memoryService.listMemories(),
        memoryService.getStats(),
      ]);
      setMemories(memoriesData.memories || []);
      setStats(statsData);
    } catch (err) {
      console.error("Failed to load memory data:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Agent Memory</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <div className="text-center">
            <p className="text-3xl font-bold text-blue-600">{stats?.total || 0}</p>
            <p className="text-sm text-gray-500">Total Memories</p>
          </div>
        </Card>
      </div>

      <Card title="Memories">
        {memories.length === 0 ? (
          <p className="text-gray-500 text-center py-4">No memories stored</p>
        ) : (
          <div className="space-y-2">
            {memories.map((memory) => (
              <div key={memory.id} className="p-3 border rounded-lg">
                <p className="text-sm">{memory.content}</p>
                <p className="text-xs text-gray-500 mt-1">Category: {memory.category}</p>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

export default AgentMemory;
