import { useState, useEffect } from "react";
import socialService from "../../services/socialService";
import Card from "../common/Card";
import Loading from "../common/Loading";

function PublishingQueue() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadQueue();
  }, []);

  const loadQueue = async () => {
    try {
      const data = await socialService.getQueue();
      setQueue(data.queue || []);
    } catch (err) {
      console.error("Failed to load queue:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Loading />;

  return (
    <Card title="Publishing Queue">
      {queue.length === 0 ? (
        <p className="text-gray-500 text-center py-4">No items in queue</p>
      ) : (
        <div className="space-y-2">
          {queue.map((item) => (
            <div key={item.id} className="p-3 border rounded-lg">
              <p className="font-medium">{item.title}</p>
              <p className="text-sm text-gray-500">{item.scheduled_at}</p>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export default PublishingQueue;
