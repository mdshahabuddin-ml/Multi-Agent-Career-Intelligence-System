import { useState, useEffect } from "react";
import videoPipelineService from "../../services/videoPipelineService";
import Card from "../common/Card";
import Loading from "../common/Loading";

const STATUS_COLORS = {
  pending: { bg: "#fef3c7", text: "#92400e" },
  script_generating: { bg: "#dbeafe", text: "#1e40af" },
  script_ready: { bg: "#dbeafe", text: "#1e40af" },
  scenes_generating: { bg: "#dbeafe", text: "#1e40af" },
  scenes_ready: { bg: "#dbeafe", text: "#1e40af" },
  video_generating: { bg: "#e0e7ff", text: "#3730a3" },
  video_ready: { bg: "#d1fae5", text: "#065f46" },
  failed: { bg: "#fee2e2", text: "#991b1b" },
  published: { bg: "#d1fae5", text: "#065f46" },
};

const APPROVAL_COLORS = {
  pending: { bg: "#fef3c7", text: "#92400e", label: "Pending" },
  approved: { bg: "#d1fae5", text: "#065f46", label: "Approved" },
  rejected: { bg: "#fee2e2", text: "#991b1b", label: "Rejected" },
};

function VideoPreview({ pipelineId, onStatusChange }) {
  const [pipeline, setPipeline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);

  useEffect(() => {
    loadPipeline();
  }, [pipelineId]);

  const loadPipeline = async () => {
    try {
      const data = await videoPipelineService.getPipeline(pipelineId);
      setPipeline(data);
    } catch (err) {
      console.error("Failed to load pipeline:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    setActionLoading("approve");
    try {
      await videoPipelineService.approveVideo(pipelineId);
      await loadPipeline();
      onStatusChange?.();
    } catch (err) {
      console.error("Approve failed:", err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async () => {
    setActionLoading("reject");
    try {
      await videoPipelineService.rejectVideo(pipelineId, "Not meeting quality standards");
      await loadPipeline();
      onStatusChange?.();
    } catch (err) {
      console.error("Reject failed:", err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRegenerate = async () => {
    setActionLoading("regenerate");
    try {
      await videoPipelineService.regenerateVideo(pipelineId);
      await loadPipeline();
      onStatusChange?.();
    } catch (err) {
      console.error("Regenerate failed:", err);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) return <Loading />;
  if (!pipeline) return null;

  const statusColor = STATUS_COLORS[pipeline.status] || STATUS_COLORS.pending;
  const approvalColor = APPROVAL_COLORS[pipeline.approval_status] || APPROVAL_COLORS.pending;
  const isShort = pipeline.metadata_json?.format === "short" || pipeline.aspect_ratio === "9:16";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Video Preview */}
      <Card title={isShort ? "Short Video Preview (9:16)" : "Video Preview (16:9)"}>
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {/* Video Player */}
          {pipeline.video_url ? (
            <div style={{
              position: "relative",
              width: "100%",
              paddingBottom: isShort ? "177.75%" : "56.25%",
              background: "#000",
              borderRadius: "0.5rem",
              overflow: "hidden",
              maxWidth: isShort ? "200px" : "100%",
              margin: isShort ? "0 auto" : "0",
            }}>
              <video
                controls
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: "100%",
                }}
                poster={pipeline.thumbnail_url}
              >
                <source src={pipeline.video_url} type="video/mp4" />
                Your browser does not support the video tag.
              </video>
            </div>
          ) : (
            <div style={{
              width: "100%",
              paddingBottom: "56.25%",
              background: "#f3f4f6",
              borderRadius: "0.5rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              position: "relative",
            }}>
              <div style={{ position: "absolute", top: "50%", transform: "translateY(-50%)", textAlign: "center" }}>
                <p style={{ color: "#6b7280", fontSize: "0.875rem" }}>
                  {pipeline.status === "video_generating" ? "Generating video..." : "No video available"}
                </p>
              </div>
            </div>
          )}

          {/* Status Bar */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <span style={{
                padding: "0.25rem 0.75rem",
                borderRadius: "9999px",
                fontSize: "0.75rem",
                fontWeight: 600,
                background: statusColor.bg,
                color: statusColor.text,
              }}>
                {pipeline.status.replace(/_/g, " ").toUpperCase()}
              </span>
            </div>
          </div>
        </div>
      </Card>

      {/* Video Approval */}
      <Card title="Video Approval">
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <p style={{ fontSize: "0.875rem", color: "#6b7280", margin: 0 }}>Status</p>
              <p style={{
                fontSize: "1rem",
                fontWeight: 600,
                color: approvalColor.text,
                margin: "0.25rem 0 0",
              }}>
                {approvalColor.label}
              </p>
            </div>
            {pipeline.approved_at && (
              <div style={{ textAlign: "right" }}>
                <p style={{ fontSize: "0.875rem", color: "#6b7280", margin: 0 }}>Approved</p>
                <p style={{ fontSize: "0.875rem", color: "#111827", margin: "0.25rem 0 0" }}>
                  {new Date(pipeline.approved_at).toLocaleString()}
                </p>
              </div>
            )}
            {pipeline.rejected_at && (
              <div style={{ textAlign: "right" }}>
                <p style={{ fontSize: "0.875rem", color: "#6b7280", margin: 0 }}>Rejected</p>
                <p style={{ fontSize: "0.875rem", color: "#991b1b", margin: "0.25rem 0 0" }}>
                  {pipeline.rejection_reason || "No reason provided"}
                </p>
              </div>
            )}
          </div>

          {/* YouTube Publishing Status */}
          {pipeline.youtube_status && (
            <div style={{
              padding: "0.75rem 1rem",
              borderRadius: "0.5rem",
              background: pipeline.youtube_status === "published" ? "#d1fae5" :
                         pipeline.youtube_status === "uploading" ? "#dbeafe" : "#fee2e2",
              color: pipeline.youtube_status === "published" ? "#065f46" :
                     pipeline.youtube_status === "uploading" ? "#1e40af" : "#991b1b",
              fontSize: "0.875rem",
            }}>
              {pipeline.youtube_status === "published" && (
                <div>
                  <p style={{ margin: 0, fontWeight: 600 }}>Published to YouTube</p>
                  {pipeline.youtube_video_url && (
                    <a
                      href={pipeline.youtube_video_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: "#2563eb", fontSize: "0.875rem" }}
                    >
                      View on YouTube
                    </a>
                  )}
                </div>
              )}
              {pipeline.youtube_status === "uploading" && (
                <p style={{ margin: 0 }}>Uploading to YouTube...</p>
              )}
              {pipeline.youtube_status === "failed" && (
                <p style={{ margin: 0 }}>YouTube upload failed</p>
              )}
            </div>
          )}

          {/* Action Buttons */}
          {pipeline.status === "video_ready" && pipeline.approval_status !== "approved" && (
            <div style={{ display: "flex", gap: "0.75rem" }}>
              <button
                onClick={handleApprove}
                disabled={actionLoading === "approve"}
                style={{
                  flex: 1,
                  padding: "0.75rem 1.5rem",
                  border: "none",
                  borderRadius: "0.5rem",
                  background: "#16a34a",
                  color: "white",
                  cursor: actionLoading === "approve" ? "not-allowed" : "pointer",
                  opacity: actionLoading === "approve" ? 0.7 : 1,
                  fontWeight: 600,
                  fontSize: "0.875rem",
                }}
              >
                {actionLoading === "approve" ? "Approving..." : "Approve Video"}
              </button>
              <button
                onClick={handleRegenerate}
                disabled={actionLoading === "regenerate"}
                style={{
                  flex: 1,
                  padding: "0.75rem 1.5rem",
                  border: "1px solid #d1d5db",
                  borderRadius: "0.5rem",
                  background: "white",
                  color: "#374151",
                  cursor: actionLoading === "regenerate" ? "not-allowed" : "pointer",
                  opacity: actionLoading === "regenerate" ? 0.7 : 1,
                  fontWeight: 600,
                  fontSize: "0.875rem",
                }}
              >
                {actionLoading === "regenerate" ? "Regenerating..." : "Regenerate"}
              </button>
            </div>
          )}

          {pipeline.status === "video_ready" && pipeline.approval_status === "approved" && (
            <div style={{
              padding: "0.75rem 1rem",
              background: "#d1fae5",
              borderRadius: "0.5rem",
              color: "#065f46",
              fontSize: "0.875rem",
              fontWeight: 500,
              textAlign: "center",
            }}>
              Video approved and ready for publishing
            </div>
          )}

          {pipeline.status === "video_generating" && (
            <div style={{
              padding: "0.75rem 1rem",
              background: "#e0e7ff",
              borderRadius: "0.5rem",
              color: "#3730a3",
              fontSize: "0.875rem",
              textAlign: "center",
            }}>
              Video is being generated... Please wait.
            </div>
          )}

          {pipeline.status === "failed" && (
            <div style={{ display: "flex", gap: "0.75rem" }}>
              <button
                onClick={handleRegenerate}
                disabled={actionLoading === "regenerate"}
                style={{
                  flex: 1,
                  padding: "0.75rem 1.5rem",
                  border: "none",
                  borderRadius: "0.5rem",
                  background: "#2563eb",
                  color: "white",
                  cursor: actionLoading === "regenerate" ? "not-allowed" : "pointer",
                  fontWeight: 600,
                  fontSize: "0.875rem",
                }}
              >
                {actionLoading === "regenerate" ? "Retrying..." : "Retry Generation"}
              </button>
            </div>
          )}
        </div>
      </Card>

      {/* Scenes Preview */}
      {pipeline.scene_details && pipeline.scene_details.length > 0 && (
        <Card title="Scenes">
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {pipeline.scene_details.map((scene) => (
              <div
                key={scene.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  padding: "0.75rem",
                  border: "1px solid #e5e7eb",
                  borderRadius: "0.5rem",
                  background: "#f9fafb",
                }}
              >
                <span style={{
                  minWidth: "1.5rem",
                  height: "1.5rem",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: "50%",
                  background: scene.status === "ready" ? "#d1fae5" : "#f3f4f6",
                  color: scene.status === "ready" ? "#065f46" : "#6b7280",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                }}>
                  {scene.scene_index + 1}
                </span>
                <div style={{ flex: 1 }}>
                  <p style={{ fontSize: "0.875rem", color: "#111827", margin: 0 }}>
                    {scene.description}
                  </p>
                  <p style={{ fontSize: "0.75rem", color: "#6b7280", margin: "0.25rem 0 0" }}>
                    {scene.duration_seconds}s | {scene.status}
                  </p>
                </div>
                {scene.video_url && (
                  <a
                    href={scene.video_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ fontSize: "0.75rem", color: "#2563eb" }}
                  >
                    View
                  </a>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

export default VideoPreview;
