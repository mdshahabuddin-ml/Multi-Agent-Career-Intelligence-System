import { useState, useEffect } from "react";
import socialService from "../services/socialService";
import contentService from "../services/contentService";
import Card from "../components/common/Card";
import Loading from "../components/common/Loading";

function ContentAnalytics() {
  const [accounts, setAccounts] = useState([]);
  const [content, setContent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [accountsData, contentData] = await Promise.all([
        socialService.listAccounts(),
        contentService.listContent(),
      ]);
      setAccounts(accountsData.accounts || []);
      setContent(contentData.content || []);
    } catch (err) {
      console.error("Failed to load data:", err);
    } finally {
      setLoading(false);
    }
  };

  const getPlatformStats = (platform) => {
    const acc = accounts.find(a => a.platform === platform);
    return {
      connected: !!acc,
      name: acc?.account_name || "",
      url: acc?.profile_data_json?.profile_url || acc?.profile_data_json?.channel_url || "",
    };
  };

  const linkedin = getPlatformStats("linkedin");
  const youtube = getPlatformStats("youtube");
  const github = getPlatformStats("github");

  if (loading) return <Loading />;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#111827" }}>Content Analytics</h2>

      {/* Stats Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem" }}>
        <div style={{ background: "white", borderRadius: "0.75rem", padding: "1.25rem", border: "1px solid #e5e7eb" }}>
          <p style={{ fontSize: "0.875rem", color: "#6b7280", margin: 0 }}>Total Content</p>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: "#111827", margin: "0.25rem 0" }}>{content.length}</p>
          <p style={{ fontSize: "0.75rem", color: "#16a34a" }}>All platforms</p>
        </div>
        <div style={{ background: "white", borderRadius: "0.75rem", padding: "1.25rem", border: "1px solid #e5e7eb" }}>
          <p style={{ fontSize: "0.875rem", color: "#6b7280", margin: 0 }}>LinkedIn</p>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: "#0a66c2", margin: "0.25rem 0" }}>{linkedin.connected ? "✓" : "—"}</p>
          <p style={{ fontSize: "0.75rem", color: linkedin.connected ? "#16a34a" : "#6b7280" }}>
            {linkedin.connected ? "Connected" : "Not connected"}
          </p>
        </div>
        <div style={{ background: "white", borderRadius: "0.75rem", padding: "1.25rem", border: "1px solid #e5e7eb" }}>
          <p style={{ fontSize: "0.875rem", color: "#6b7280", margin: 0 }}>YouTube</p>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: "#ff0000", margin: "0.25rem 0" }}>{youtube.connected ? "✓" : "—"}</p>
          <p style={{ fontSize: "0.75rem", color: youtube.connected ? "#16a34a" : "#6b7280" }}>
            {youtube.connected ? "Connected" : "Not connected"}
          </p>
        </div>
        <div style={{ background: "white", borderRadius: "0.75rem", padding: "1.25rem", border: "1px solid #e5e7eb" }}>
          <p style={{ fontSize: "0.875rem", color: "#6b7280", margin: 0 }}>GitHub</p>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: "#24292e", margin: "0.25rem 0" }}>{github.connected ? "✓" : "—"}</p>
          <p style={{ fontSize: "0.75rem", color: github.connected ? "#16a34a" : "#6b7280" }}>
            {github.connected ? "Connected" : "Not connected"}
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: "0.5rem", borderBottom: "2px solid #e5e7eb", paddingBottom: "0" }}>
        {["overview", "youtube", "linkedin", "github"].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: "0.75rem 1.25rem",
              border: "none",
              background: "none",
              cursor: "pointer",
              fontWeight: 600,
              fontSize: "0.875rem",
              color: activeTab === tab ? "#2563eb" : "#6b7280",
              borderBottom: activeTab === tab ? "2px solid #2563eb" : "2px solid transparent",
              marginBottom: "-2px",
            }}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "overview" && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1rem" }}>
          <Card title="Connected Platforms">
            {accounts.length === 0 ? (
              <p style={{ color: "#6b7280", textAlign: "center", padding: "1rem" }}>No platforms connected</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {accounts.map(acc => (
                  <div key={acc.id} style={{ display: "flex", alignItems: "center", gap: "0.75rem", padding: "0.5rem" }}>
                    <div style={{
                      width: "32px", height: "32px", borderRadius: "0.375rem",
                      background: acc.platform === "linkedin" ? "#0a66c2" : acc.platform === "youtube" ? "#ff0000" : "#24292e",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      color: "white", fontWeight: 700, fontSize: "0.75rem"
                    }}>
                      {acc.platform === "linkedin" ? "in" : acc.platform === "youtube" ? "YT" : "GH"}
                    </div>
                    <div>
                      <p style={{ fontWeight: 600, margin: 0, fontSize: "0.875rem" }}>{acc.platform}</p>
                      <p style={{ color: "#6b7280", margin: 0, fontSize: "0.75rem" }}>{acc.account_name}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card title="Recent Content">
            {content.length === 0 ? (
              <p style={{ color: "#6b7280", textAlign: "center", padding: "1rem" }}>No content yet. Create your first post!</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {content.slice(0, 5).map(item => (
                  <div key={item.id} style={{ padding: "0.5rem", borderBottom: "1px solid #f3f4f6" }}>
                    <p style={{ fontWeight: 600, margin: 0, fontSize: "0.875rem" }}>{item.title}</p>
                    <p style={{ color: "#6b7280", margin: 0, fontSize: "0.75rem" }}>{item.content_type}</p>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {activeTab === "youtube" && (
        <Card title="YouTube Content">
          {youtube.connected ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "1rem", padding: "1rem", background: "#fff5f5", borderRadius: "0.5rem" }}>
                <div style={{ width: "48px", height: "48px", borderRadius: "0.5rem", background: "#ff0000", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 700 }}>
                  YT
                </div>
                <div>
                  <p style={{ fontWeight: 600, margin: 0 }}>{youtube.name}</p>
                  <a href={youtube.url} target="_blank" rel="noopener noreferrer" style={{ color: "#2563eb", fontSize: "0.875rem" }}>View Channel</a>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
                <div style={{ textAlign: "center", padding: "1rem", background: "#f9fafb", borderRadius: "0.5rem" }}>
                  <p style={{ fontSize: "1.5rem", fontWeight: 700, color: "#111827", margin: 0 }}>0</p>
                  <p style={{ color: "#6b7280", fontSize: "0.875rem", margin: 0 }}>Videos</p>
                </div>
                <div style={{ textAlign: "center", padding: "1rem", background: "#f9fafb", borderRadius: "0.5rem" }}>
                  <p style={{ fontSize: "1.5rem", fontWeight: 700, color: "#111827", margin: 0 }}>0</p>
                  <p style={{ color: "#6b7280", fontSize: "0.875rem", margin: 0 }}>Views</p>
                </div>
                <div style={{ textAlign: "center", padding: "1rem", background: "#f9fafb", borderRadius: "0.5rem" }}>
                  <p style={{ fontSize: "1.5rem", fontWeight: 700, color: "#111827", margin: 0 }}>0</p>
                  <p style={{ color: "#6b7280", fontSize: "0.875rem", margin: 0 }}>Subscribers</p>
                </div>
              </div>

              <p style={{ color: "#6b7280", textAlign: "center", padding: "2rem", fontSize: "0.875rem" }}>
                YouTube analytics will appear here once you publish content
              </p>
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "3rem" }}>
              <p style={{ color: "#6b7280", marginBottom: "1rem" }}>YouTube not connected</p>
              <a href="/social" style={{ color: "#2563eb", fontWeight: 600 }}>Connect YouTube →</a>
            </div>
          )}
        </Card>
      )}

      {activeTab === "linkedin" && (
        <Card title="LinkedIn Content">
          {linkedin.connected ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "1rem", padding: "1rem", background: "#f0f7ff", borderRadius: "0.5rem" }}>
                <div style={{ width: "48px", height: "48px", borderRadius: "0.5rem", background: "#0a66c2", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 700, fontSize: "1.25rem" }}>
                  in
                </div>
                <div>
                  <p style={{ fontWeight: 600, margin: 0 }}>{linkedin.name}</p>
                  <a href={linkedin.url} target="_blank" rel="noopener noreferrer" style={{ color: "#2563eb", fontSize: "0.875rem" }}>View Profile</a>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
                <div style={{ textAlign: "center", padding: "1rem", background: "#f9fafb", borderRadius: "0.5rem" }}>
                  <p style={{ fontSize: "1.5rem", fontWeight: 700, color: "#111827", margin: 0 }}>0</p>
                  <p style={{ color: "#6b7280", fontSize: "0.875rem", margin: 0 }}>Posts</p>
                </div>
                <div style={{ textAlign: "center", padding: "1rem", background: "#f9fafb", borderRadius: "0.5rem" }}>
                  <p style={{ fontSize: "1.5rem", fontWeight: 700, color: "#111827", margin: 0 }}>0</p>
                  <p style={{ color: "#6b7280", fontSize: "0.875rem", margin: 0 }}>Impressions</p>
                </div>
                <div style={{ textAlign: "center", padding: "1rem", background: "#f9fafb", borderRadius: "0.5rem" }}>
                  <p style={{ fontSize: "1.5rem", fontWeight: 700, color: "#111827", margin: 0 }}>0</p>
                  <p style={{ color: "#6b7280", fontSize: "0.875rem", margin: 0 }}>Engagement</p>
                </div>
              </div>

              <p style={{ color: "#6b7280", textAlign: "center", padding: "2rem", fontSize: "0.875rem" }}>
                LinkedIn analytics will appear here once you publish content
              </p>
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "3rem" }}>
              <p style={{ color: "#6b7280", marginBottom: "1rem" }}>LinkedIn not connected</p>
              <a href="/social" style={{ color: "#2563eb", fontWeight: 600 }}>Connect LinkedIn →</a>
            </div>
          )}
        </Card>
      )}

      {activeTab === "github" && (
        <Card title="GitHub Activity">
          {github.connected ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "1rem", padding: "1rem", background: "#f6f8fa", borderRadius: "0.5rem" }}>
                <div style={{ width: "48px", height: "48px", borderRadius: "0.5rem", background: "#24292e", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 700 }}>
                  GH
                </div>
                <div>
                  <p style={{ fontWeight: 600, margin: 0 }}>{github.name}</p>
                  <a href={github.url} target="_blank" rel="noopener noreferrer" style={{ color: "#2563eb", fontSize: "0.875rem" }}>View Profile</a>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
                <div style={{ textAlign: "center", padding: "1rem", background: "#f9fafb", borderRadius: "0.5rem" }}>
                  <p style={{ fontSize: "1.5rem", fontWeight: 700, color: "#111827", margin: 0 }}>0</p>
                  <p style={{ color: "#6b7280", fontSize: "0.875rem", margin: 0 }}>Repos</p>
                </div>
                <div style={{ textAlign: "center", padding: "1rem", background: "#f9fafb", borderRadius: "0.5rem" }}>
                  <p style={{ fontSize: "1.5rem", fontWeight: 700, color: "#111827", margin: 0 }}>0</p>
                  <p style={{ color: "#6b7280", fontSize: "0.875rem", margin: 0 }}>Stars</p>
                </div>
                <div style={{ textAlign: "center", padding: "1rem", background: "#f9fafb", borderRadius: "0.5rem" }}>
                  <p style={{ fontSize: "1.5rem", fontWeight: 700, color: "#111827", margin: 0 }}>0</p>
                  <p style={{ color: "#6b7280", fontSize: "0.875rem", margin: 0 }}>Contributions</p>
                </div>
              </div>

              <p style={{ color: "#6b7280", textAlign: "center", padding: "2rem", fontSize: "0.875rem" }}>
                GitHub activity will appear here
              </p>
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "3rem" }}>
              <p style={{ color: "#6b7280", marginBottom: "1rem" }}>GitHub not connected</p>
              <a href="/social" style={{ color: "#2563eb", fontWeight: 600 }}>Connect GitHub →</a>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

export default ContentAnalytics;
