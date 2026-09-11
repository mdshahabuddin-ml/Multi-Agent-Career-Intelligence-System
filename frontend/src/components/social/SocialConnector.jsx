import { useState } from "react";
import socialService from "../../services/socialService";
import Card from "../common/Card";

function SocialConnector() {
  const [platform, setPlatform] = useState("linkedin");
  const [profileUrl, setProfileUrl] = useState("https://www.linkedin.com/in/md-shahabuddin-aiml/");
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleConnect = async () => {
    setConnecting(true);
    setError(null);
    setSuccess(null);

    try {
      let data;
      if (platform === "linkedin") {
        data = await socialService.manualConnectLinkedIn(profileUrl);
      } else if (platform === "youtube") {
        data = await socialService.manualConnectYouTube(profileUrl);
      } else if (platform === "github") {
        data = await socialService.manualConnectGitHub(profileUrl);
      } else {
        const redirectUri = `${window.location.origin}/social/callback`;
        data = await socialService.connectAccount(platform, redirectUri);
        if (data.authorization_url) {
          window.location.href = data.authorization_url;
          return;
        }
      }
      if (data.success || data.id) {
        setSuccess(`${platform.charAt(0).toUpperCase() + platform.slice(1)} connected successfully!`);
        setProfileUrl("");
      }
    } catch (err) {
      console.error("Failed to connect:", err);
      const msg = err.response?.data?.detail || err.message || "Failed to connect";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setConnecting(false);
    }
  };

  const getPlaceholder = () => {
    switch (platform) {
      case "linkedin":
        return "https://www.linkedin.com/in/your-profile";
      case "youtube":
        return "https://www.youtube.com/@your-channel";
      case "github":
        return "https://github.com/your-username";
      default:
        return "Enter URL";
    }
  };

  const getLabel = () => {
    switch (platform) {
      case "linkedin":
        return "LinkedIn Profile URL";
      case "youtube":
        return "YouTube Channel URL";
      case "github":
        return "GitHub Profile URL";
      default:
        return "Profile URL";
    }
  };

  return (
    <Card title="Connect Social Account">
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        {error && (
          <div style={{ color: "#dc2626", fontSize: "0.875rem", padding: "0.75rem", background: "#fef2f2", borderRadius: "0.5rem" }}>
            {error}
          </div>
        )}
        {success && (
          <div style={{ color: "#16a34a", fontSize: "0.875rem", padding: "0.75rem", background: "#f0fdf4", borderRadius: "0.5rem" }}>
            {success}
          </div>
        )}
        <select
          value={platform}
          onChange={(e) => {
            setPlatform(e.target.value);
            setProfileUrl("");
            setError(null);
            setSuccess(null);
          }}
          style={{ width: "100%", padding: "0.5rem 0.75rem", border: "1px solid #d1d5db", borderRadius: "0.5rem" }}
        >
          <option value="linkedin">LinkedIn</option>
          <option value="youtube">YouTube</option>
          <option value="github">GitHub</option>
          <option value="instagram">Instagram</option>
          <option value="facebook">Facebook</option>
        </select>

        {(platform === "linkedin" || platform === "youtube" || platform === "github") && (
          <div>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, color: "#374151", marginBottom: "0.25rem" }}>
              {getLabel()}
            </label>
            <input
              type="url"
              value={profileUrl}
              onChange={(e) => setProfileUrl(e.target.value)}
              placeholder={getPlaceholder()}
              style={{ width: "100%", padding: "0.5rem 0.75rem", border: "1px solid #d1d5db", borderRadius: "0.5rem" }}
            />
          </div>
        )}

        <button
          onClick={handleConnect}
          disabled={connecting || (!profileUrl && (platform === "linkedin" || platform === "youtube" || platform === "github"))}
          style={{
            background: "#2563eb",
            color: "white",
            border: "none",
            padding: "0.75rem 1.5rem",
            borderRadius: "0.5rem",
            cursor: connecting ? "not-allowed" : "pointer",
            fontWeight: 600,
            opacity: connecting ? 0.7 : 1,
            alignSelf: "flex-start"
          }}
        >
          {connecting ? "Connecting..." : `Connect ${platform}`}
        </button>
      </div>
    </Card>
  );
}

export default SocialConnector;
