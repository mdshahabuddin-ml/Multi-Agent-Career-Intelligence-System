import { useState, useEffect } from "react";
import contentService from "../../services/contentService";
import Card from "../common/Card";
import Loading from "../common/Loading";

function ContentDashboard() {
  const [content, setContent] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadContent();
  }, []);

  const loadContent = async () => {
    try {
      const data = await contentService.listContent();
      setContent(data.content || []);
    } catch (err) {
      console.error("Failed to load content:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Content Dashboard</h2>

      <Card title="Content Items">
        {content.length === 0 ? (
          <p className="text-gray-500 text-center py-4">No content items</p>
        ) : (
          <div className="space-y-2">
            {content.map((item) => (
              <div key={item.id} className="p-3 border rounded-lg">
                <p className="font-medium">{item.title}</p>
                <p className="text-sm text-gray-500">{item.content_type}</p>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

export default ContentDashboard;
