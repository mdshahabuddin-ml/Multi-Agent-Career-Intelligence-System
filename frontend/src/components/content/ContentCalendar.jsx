import { useState, useEffect } from "react";
import Card from "../common/Card";
import Loading from "../common/Loading";

function ContentCalendar() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEvents();
  }, []);

  const loadEvents = async () => {
    try {
      setEvents([]);
    } catch (err) {
      console.error("Failed to load events:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Loading />;

  return (
    <Card title="Content Calendar">
      {events.length === 0 ? (
        <p className="text-gray-500 text-center py-4">No scheduled content</p>
      ) : (
        <div className="space-y-2">
          {events.map((event) => (
            <div key={event.id} className="p-3 border rounded-lg">
              <p className="font-medium">{event.title}</p>
              <p className="text-sm text-gray-500">{event.date}</p>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export default ContentCalendar;
