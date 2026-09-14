import { useState, useEffect } from "react";
import contentService from "../services/contentService";
import publishingService from "../services/publishingService";
import videoPipelineService from "../services/videoPipelineService";
import Card from "../components/common/Card";
import Loading from "../components/common/Loading";
import VideoPreview from "../components/content/VideoPreview";

function Content() {
  const [content, setContent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(null);
  const [publishResult, setPublishResult] = useState(null);
  const [showPublishModal, setShowPublishModal] = useState(false);
  const [selectedContent, setSelectedContent] = useState(null);
  const [publishForm, setPublishForm] = useState({
    title: "",
    description: "",
    videoUrl: "",
    tags: "",
    privacy: "unlisted",
  });
  const [pipelines, setPipelines] = useState({});
  const [generatingVideo, setGeneratingVideo] = useState(null);
  const [selectedPipeline, setSelectedPipeline] = useState(null);

  useEffect(() => {
    loadContent();
    loadPipelines();
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

  const loadPipelines = async () => {
    try {
      const data = await videoPipelineService.listPipelines();
      const pipelineMap = {};
      (data.pipelines || []).forEach((p) => {
        pipelineMap[p.content_id] = p;
      });
      setPipelines(pipelineMap);
    } catch (err) {
      console.error("Failed to load pipelines:", err);
    }
  };

  const handleApprove = async (contentId) => {
    try {
      await contentService.updateContent(contentId, { status: "approved" });
      loadContent();
    } catch (err) {
      console.error("Failed to approve:", err);
    }
  };

  const handleGenerateVideo = async (contentId) => {
    setGeneratingVideo(contentId);
    try {
      await videoPipelineService.startPipeline(contentId);
      loadPipelines();
    } catch (err) {
      console.error("Failed to generate video:", err);
    } finally {
      setGeneratingVideo(null);
    }
  };

  const handleGenerateShort = async (contentId) => {
    setGeneratingVideo(contentId);
    try {
      await videoPipelineService.startShortPipeline(contentId);
      loadPipelines();
    } catch (err) {
      console.error("Failed to generate short:", err);
    } finally {
      setGeneratingVideo(null);
    }
  };

  const openPublishModal = (item) => {
    setSelectedContent(item);
    setPublishForm({
      title: item.title || "",
      description: item.body || "",
      videoUrl: "",
      tags: (item.tags_json || []).join(", "),
      privacy: "unlisted",
    });
    setShowPublishModal(true);
    setPublishResult(null);
  };

  const handlePublish = async () => {
    if (!selectedContent) return;
    setPublishing(selectedContent.id);
    setPublishResult(null);

    try {
      const result = await publishingService.publishToYouTube({
        contentId: selectedContent.id,
        title: publishForm.title,
        description: publishForm.description,
        videoUrl: publishForm.videoUrl || null,
        tags: publishForm.tags.split(",").map(t => t.trim()).filter(Boolean),
        privacy: publishForm.privacy,
      });
      setPublishResult(result);
      if (result.success) {
        loadContent();
      }
    } catch (err) {
      console.error("Publish failed:", err);
      const msg = err.response?.data?.detail || err.message || "Publish failed";
      setPublishResult({ success: false, message: typeof msg === "string" ? msg : JSON.stringify(msg) });
    } finally {
      setPublishing(null);
    }
  };

  if (loading) return <Loading />;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#111827" }}>Content</h2>

      <Card title="Content Items">
        {content.length === 0 ? (
          <p style={{ color: "#6b7280", textAlign: "center", padding: "1rem" }}>No content items</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {content.map((item) => (
              <div
                key={item.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "1rem",
                  border: "1px solid #e5e7eb",
                  borderRadius: "0.5rem",
                  background: "#f9fafb",
                }}
              >
                <div style={{ flex: 1 }}>
                  <p style={{ fontWeight: 600, color: "#111827", margin: 0 }}>{item.title}</p>
                  <p style={{ fontSize: "0.875rem", color: "#6b7280", margin: "0.25rem 0 0" }}>
                    {item.content_type} • {item.status}
                  </p>
                </div>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  {item.status === "draft" && (
                    <button
                      onClick={() => handleApprove(item.id)}
                      style={{
                        padding: "0.375rem 0.75rem",
                        fontSize: "0.75rem",
                        background: "#16a34a",
                        color: "white",
                        border: "none",
                        borderRadius: "0.25rem",
                        cursor: "pointer",
                        fontWeight: 500,
                      }}
                    >
                      Approve
                    </button>
                  )}
                  {item.status === "approved" && !pipelines[item.id] && (
                    <>
                      <button
                        onClick={() => handleGenerateVideo(item.id)}
                        disabled={generatingVideo === item.id}
                        style={{
                          padding: "0.375rem 0.75rem",
                          fontSize: "0.75rem",
                          background: "#2563eb",
                          color: "white",
                          border: "none",
                          borderRadius: "0.25rem",
                          cursor: generatingVideo === item.id ? "not-allowed" : "pointer",
                          opacity: generatingVideo === item.id ? 0.7 : 1,
                          fontWeight: 500,
                        }}
                      >
                        {generatingVideo === item.id ? "Generating..." : "Generate Video"}
                      </button>
                      <button
                        onClick={() => handleGenerateShort(item.id)}
                        disabled={generatingVideo === item.id}
                        style={{
                          padding: "0.375rem 0.75rem",
                          fontSize: "0.75rem",
                          background: "#7c3aed",
                          color: "white",
                          border: "none",
                          borderRadius: "0.25rem",
                          cursor: generatingVideo === item.id ? "not-allowed" : "pointer",
                          opacity: generatingVideo === item.id ? 0.7 : 1,
                          fontWeight: 500,
                        }}
                      >
                        {generatingVideo === item.id ? "Generating..." : "Create Short"}
                      </button>
                    </>
                  )}
                  {item.status === "approved" && pipelines[item.id] && (
                    <button
                      onClick={() => setSelectedPipeline(pipelines[item.id])}
                      style={{
                        padding: "0.375rem 0.75rem",
                        fontSize: "0.75rem",
                        background: pipelines[item.id].status === "video_ready" ? "#16a34a" : "#6b7280",
                        color: "white",
                        border: "none",
                        borderRadius: "0.25rem",
                        cursor: "pointer",
                        fontWeight: 500,
                      }}
                    >
                      {pipelines[item.id].status === "video_ready" ? "View Video" : pipelines[item.id].status.replace(/_/g, " ")}
                    </button>
                  )}
                  {item.status === "approved" && (
                    <button
                      onClick={() => openPublishModal(item)}
                      style={{
                        padding: "0.375rem 0.75rem",
                        fontSize: "0.75rem",
                        background: "#ff0000",
                        color: "white",
                        border: "none",
                        borderRadius: "0.25rem",
                        cursor: "pointer",
                        fontWeight: 500,
                      }}
                    >
                      Publish to YouTube
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Publish Modal */}
      {showPublishModal && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center",
          justifyContent: "center", zIndex: 1000,
        }}>
          <div style={{
            background: "white", borderRadius: "0.75rem", padding: "1.5rem",
            width: "100%", maxWidth: "500px", maxHeight: "90vh", overflow: "auto",
          }}>
            <h3 style={{ fontSize: "1.125rem", fontWeight: 600, margin: "0 0 1rem" }}>
              Publish to YouTube
            </h3>

            {publishResult && (
              <div style={{
                padding: "0.75rem", borderRadius: "0.5rem", marginBottom: "1rem",
                background: publishResult.success ? "#f0fdf4" : "#fef2f2",
                color: publishResult.success ? "#166534" : "#991b1b",
                fontSize: "0.875rem",
              }}>
                {publishResult.success ? (
                  <>
                    Published! Video ID: {publishResult.platform_post_id}
                    {publishResult.platform_post_url && (
                      <a href={publishResult.platform_post_url} target="_blank" rel="noopener noreferrer"
                        style={{ display: "block", marginTop: "0.25rem", color: "#2563eb" }}>
                        View on YouTube
                      </a>
                    )}
                  </>
                ) : (
                  publishResult.message
                )}
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.25rem" }}>
                  Title *
                </label>
                <input
                  value={publishForm.title}
                  onChange={(e) => setPublishForm({ ...publishForm, title: e.target.value })}
                  style={{ width: "100%", padding: "0.5rem", border: "1px solid #d1d5db", borderRadius: "0.375rem" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.25rem" }}>
                  Description
                </label>
                <textarea
                  value={publishForm.description}
                  onChange={(e) => setPublishForm({ ...publishForm, description: e.target.value })}
                  rows={3}
                  style={{ width: "100%", padding: "0.5rem", border: "1px solid #d1d5db", borderRadius: "0.375rem" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.25rem" }}>
                  Video URL
                </label>
                <input
                  value={publishForm.videoUrl}
                  onChange={(e) => setPublishForm({ ...publishForm, videoUrl: e.target.value })}
                  placeholder="https://example.com/video.mp4"
                  style={{ width: "100%", padding: "0.5rem", border: "1px solid #d1d5db", borderRadius: "0.375rem" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.25rem" }}>
                  Tags (comma separated)
                </label>
                <input
                  value={publishForm.tags}
                  onChange={(e) => setPublishForm({ ...publishForm, tags: e.target.value })}
                  placeholder="career, AI, tech"
                  style={{ width: "100%", padding: "0.5rem", border: "1px solid #d1d5db", borderRadius: "0.375rem" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.25rem" }}>
                  Privacy
                </label>
                <select
                  value={publishForm.privacy}
                  onChange={(e) => setPublishForm({ ...publishForm, privacy: e.target.value })}
                  style={{ width: "100%", padding: "0.5rem", border: "1px solid #d1d5db", borderRadius: "0.375rem" }}
                >
                  <option value="private">Private</option>
                  <option value="unlisted">Unlisted</option>
                  <option value="public">Public</option>
                </select>
              </div>
            </div>

            <div style={{ display: "flex", gap: "0.5rem", marginTop: "1.5rem", justifyContent: "flex-end" }}>
              <button
                onClick={() => setShowPublishModal(false)}
                style={{
                  padding: "0.5rem 1rem", border: "1px solid #d1d5db", borderRadius: "0.375rem",
                  background: "white", cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handlePublish}
                disabled={publishing || !publishForm.title}
                style={{
                  padding: "0.5rem 1rem", border: "none", borderRadius: "0.375rem",
                  background: "#ff0000", color: "white", cursor: publishing ? "not-allowed" : "pointer",
                  opacity: publishing || !publishForm.title ? 0.7 : 1,
                  fontWeight: 600,
                }}
              >
                {publishing ? "Publishing..." : "Publish"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Video Preview Modal */}
      {selectedPipeline && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center",
          justifyContent: "center", zIndex: 1000,
        }}>
          <div style={{
            background: "white", borderRadius: "0.75rem", padding: "1.5rem",
            width: "100%", maxWidth: "600px", maxHeight: "90vh", overflow: "auto",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h3 style={{ fontSize: "1.125rem", fontWeight: 600, margin: 0 }}>Video Preview</h3>
              <button
                onClick={() => setSelectedPipeline(null)}
                style={{
                  background: "none", border: "none", fontSize: "1.25rem",
                  cursor: "pointer", color: "#6b7280",
                }}
              >
                ×
              </button>
            </div>
            <VideoPreview
              pipelineId={selectedPipeline.id}
              onStatusChange={() => {
                loadPipelines();
                setSelectedPipeline(null);
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default Content;
