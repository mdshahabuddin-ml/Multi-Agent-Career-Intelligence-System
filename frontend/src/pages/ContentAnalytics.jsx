import { useState, useEffect } from "react";
import socialService from "../services/socialService";
import contentService from "../services/contentService";
import Card from "../components/common/Card";
import Loading from "../components/common/Loading";
import ErrorMessage from "../components/common/ErrorMessage";

const PLATFORMS = [
  { id: "linkedin", label: "LinkedIn", icon: "in", iconBg: "#0a66c2" },
  { id: "youtube", label: "YouTube", icon: "▶", iconBg: "#ff0000" },
  { id: "github", label: "GitHub", icon: "GH", iconBg: "#24292e" },
];

function platformLabel(id) {
  return PLATFORMS.find(p => p.id === id)?.label || (id.charAt(0).toUpperCase() + id.slice(1));
}

function platformBrand(id) {
  return PLATFORMS.find(p => p.id === id) || { label: platformLabel(id), icon: id.charAt(0).toUpperCase(), iconBg: "#6b7280" };
}

function formatLabel(value) {
  if (value === null || value === undefined) return "";
  return String(value).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDate(value) {
  if (!value) return "";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function ContentAnalytics() {
  const [accounts, setAccounts] = useState([]);
  const [content, setContent] = useState([]);
  const [totalContent, setTotalContent] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");

  const loadData = async () => {
    try {
      setError(null);
      setLoading(true);
      const [accountsData, contentData] = await Promise.all([
        socialService.listAccounts(),
        contentService.listContent(),
      ]);
      setAccounts(accountsData.accounts || []);
      setContent(contentData.content || []);
      setTotalContent(
        typeof contentData.total === "number" ? contentData.total : (contentData.content || []).length
      );
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to load analytics");
      console.error("Failed to load data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const getPlatformStats = (platform) => {
    const acc = accounts.find(a => a.platform === platform);
    return {
      connected: !!acc,
      name: acc?.account_name || "",
      url: acc?.profile_data_json?.profile_url || acc?.profile_data_json?.channel_url || "",
    };
  };

  const thisMonthCount = content.filter(item => {
    if (!item.created_at) return false;
    const d = new Date(item.created_at);
    const now = new Date();
    return !Number.isNaN(d.getTime()) && d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
  }).length;

  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "youtube", label: "YouTube" },
    { id: "linkedin", label: "LinkedIn" },
    { id: "github", label: "GitHub" },
  ];

  if (loading) return <Loading />;
  if (error) return (
    <div className="page analytics-page">
      <div className="analytics-head">
        <h1>Content Analytics</h1>
      </div>
      <Card>
        <ErrorMessage message={error} />
        <div className="analytics-retry">
          <button type="button" className="analytics-ghostbtn" onClick={loadData}>Retry</button>
        </div>
      </Card>
    </div>
  );

  return (
    <div className="page analytics-page">
      <div className="analytics-head">
        <div>
          <h1>Content Analytics</h1>
          <p>Performance and presence across your connected platforms.</p>
        </div>
      </div>

      {/* Summary cards */}
      <div className="analytics-summary">
        <div className="analytics-summary-card primary">
          <div className="analytics-summary-top">
            <span className="analytics-summary-icon" aria-hidden="true">◉</span>
            <span className="analytics-summary-label">Total Content</span>
          </div>
          <p className="analytics-summary-value">{totalContent}</p>
          <p className="analytics-summary-sub">
            Across all connected platforms{thisMonthCount > 0 ? ` · +${thisMonthCount} this month` : ""}
          </p>
        </div>
        {PLATFORMS.map(p => {
          const s = getPlatformStats(p.id);
          return (
            <div key={p.id} className="analytics-summary-card">
              <div className="analytics-summary-top">
                <span className="analytics-platform-icon" style={{ background: p.iconBg }} aria-hidden="true">
                  {p.icon}
                </span>
                <span className="analytics-summary-label">{p.label}</span>
              </div>
              <p className={`analytics-connection ${s.connected ? "on" : "off"}`}>
                <span aria-hidden="true">{s.connected ? "●" : "○"}</span> {s.connected ? "Connected" : "Not connected"}
              </p>
              <p className="analytics-summary-sub truncate" title={s.name}>{s.connected ? s.name : "—"}</p>
            </div>
          );
        })}
      </div>

      {/* Tabs */}
      <div className="analytics-tabs" role="tablist" aria-label="Analytics views">
        {tabs.map(tab => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`analytics-tab ${activeTab === tab.id ? "active" : ""}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "overview" && (
        <div className="analytics-panels">
          <Card title="Connected Platforms">
            {accounts.length === 0 ? (
              <div className="analytics-empty slim">
                <h3>No platforms connected</h3>
                <p>Connect a platform to see it here.</p>
              </div>
            ) : (
              <div className="analytics-platform-list">
                {accounts.map(acc => {
                  const brand = platformBrand(acc.platform);
                  return (
                    <div key={acc.id} className="analytics-platform-row">
                      <span className="analytics-platform-icon sm" style={{ background: brand.iconBg }} aria-hidden="true">
                        {brand.icon}
                      </span>
                      <div className="analytics-platform-info">
                        <p className="analytics-platform-name">{brand.label}</p>
                        <p className="analytics-platform-user">{acc.account_name}</p>
                      </div>
                      <span className="analytics-connection on sm">
                        <span aria-hidden="true">●</span> Connected
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>

          <Card title="Recent Content">
            {content.length === 0 ? (
              <div className="analytics-empty slim">
                <h3>No content yet</h3>
                <p>No content yet. Create your first post!</p>
              </div>
            ) : (
              <div className="analytics-feed">
                {content.slice(0, 5).map(item => (
                  <div key={item.id} className="analytics-feed-item">
                    <p className="analytics-feed-title">{item.title}</p>
                    <p className="analytics-feed-meta">
                      {[formatLabel(item.content_type), formatDate(item.created_at)].filter(Boolean).join(" · ")}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {["youtube", "linkedin", "github"].includes(activeTab) && (
        <PlatformPanel
          platformId={activeTab}
          stats={getPlatformStats(activeTab)}
        />
      )}
    </div>
  );
}

function PlatformPanel({ platformId, stats }) {
  const brand = platformBrand(platformId);
  const actionLabel = platformId === "youtube" ? "View Channel" : "View Profile";
  const connectLabel = `Connect ${brand.label} →`;
  if (!stats.connected) {
    return (
      <Card title={`${brand.label} Content`}>
        <div className="analytics-empty">
          <div className="analytics-empty-icon" aria-hidden="true">{brand.icon}</div>
          <h3>{brand.label} not connected</h3>
          <p>Connect your {brand.label} account to see analytics here.</p>
          <a href="/social" className="analytics-connect-link">{connectLabel}</a>
        </div>
      </Card>
    );
  }
  return (
    <Card title={`${brand.label} Content`}>
      <div className="analytics-account-head">
        <span className="analytics-platform-icon lg" style={{ background: brand.iconBg }} aria-hidden="true">
          {brand.icon}
        </span>
        <div>
          <p className="analytics-account-name">{stats.name}</p>
          {stats.url && (
            <a href={stats.url} target="_blank" rel="noopener noreferrer" className="analytics-account-link">
              {actionLabel}
            </a>
          )}
        </div>
        <span className="analytics-connection on">
          <span aria-hidden="true">●</span> Connected
        </span>
      </div>
      <div className="analytics-empty slim">
        <h3>Analytics coming soon</h3>
        <p>{brand.label} analytics will appear here once you publish content.</p>
      </div>
    </Card>
  );
}

export default ContentAnalytics;
