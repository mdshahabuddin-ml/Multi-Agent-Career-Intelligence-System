import { useState, useEffect } from "react";
import socialService from "../../services/socialService";
import Card from "../common/Card";
import Loading from "../common/Loading";

function PublishingStatus() {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPosts();
  }, []);

  const loadPosts = async () => {
    try {
      const data = await socialService.listPosts();
      setPosts(data.posts || []);
    } catch (err) {
      console.error("Failed to load posts:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Loading />;

  return (
    <Card title="Publishing Status">
      {posts.length === 0 ? (
        <p className="text-gray-500 text-center py-4">No published posts</p>
      ) : (
        <div className="space-y-2">
          {posts.map((post) => (
            <div key={post.id} className="p-3 border rounded-lg">
              <p className="font-medium">{post.content_text?.substring(0, 50)}...</p>
              <p className="text-sm text-gray-500">{post.status}</p>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export default PublishingStatus;
