import { useState, useEffect } from "react";
import socialService from "../../services/socialService";
import Card from "../common/Card";
import Loading from "../common/Loading";

const PLATFORM_META = {
  linkedin: { desc: "Professional profile" },
  youtube: { desc: "Content channel" },
  github: { desc: "Developer profile" },
  instagram: { desc: "Social profile" },
  facebook: { desc: "Social profile" },
};

function SocialAccounts() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      const data = await socialService.listAccounts();
      setAccounts(data.accounts || []);
    } catch (err) {
      console.error("Failed to load accounts:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async (accountId) => {
    try {
      await socialService.disconnectAccount(accountId);
      setAccounts(accounts.filter(a => a.id !== accountId));
    } catch (err) {
      console.error("Failed to disconnect:", err);
    }
  };

  const getPlatformIcon = (platform) => {
    switch (platform) {
      case "linkedin":
        return { bg: "#0a66c2", text: "in", color: "white" };
      case "youtube":
        return { bg: "#ff0000", text: "YT", color: "white" };
      case "github":
        return { bg: "#24292e", text: "GH", color: "white" };
      case "instagram":
        return { bg: "#E4405F", text: "IG", color: "white" };
      case "facebook":
        return { bg: "#1877F2", text: "FB", color: "white" };
      default:
        return { bg: "#6b7280", text: platform.charAt(0).toUpperCase(), color: "white" };
    }
  };

  const getProfileUrl = (account) => {
    if (account.profile_data_json?.profile_url) {
      return account.profile_data_json.profile_url;
    }
    if (account.profile_data_json?.channel_url) {
      return account.profile_data_json.channel_url;
    }
    return null;
  };

  // Render the actual connection state when the API provides one;
  // listed accounts without a status field are connected accounts.
  const statusOf = (account) => {
    const raw = account.status || account.state || "connected";
    const key = String(raw).toLowerCase();
    if (["connecting", "pending", "authorizing"].includes(key)) {
      return { key: "connecting", label: "Connecting…", tone: "amber", dot: "🔄" };
    }
    if (["error", "failed", "expired", "revoked"].includes(key)) {
      return { key: "error", label: "Connection Error", tone: "red", dot: "⚠" };
    }
    if (["disconnected", "inactive", "disabled"].includes(key)) {
      return { key: "disconnected", label: "Not Connected", tone: "muted", dot: "⚪" };
    }
    return { key: "connected", label: "Connected", tone: "green", dot: "●" };
  };

  if (loading) return <Loading />;

  return (
    <Card title="Social Accounts">
      {accounts.length === 0 ? (
        <div className="social-empty">
          <div className="social-empty-icon" aria-hidden="true">🔗</div>
          <h3>No accounts connected</h3>
          <p>Connect your social profiles using the form below to manage your professional presence.</p>
        </div>
      ) : (
        <div className="social-tiles">
          {accounts.map((account) => {
            const icon = getPlatformIcon(account.platform);
            const profileUrl = getProfileUrl(account);
            const platformName = account.platform.charAt(0).toUpperCase() + account.platform.slice(1);
            const platformDesc = PLATFORM_META[account.platform]?.desc || "";
            const status = statusOf(account);
            return (
              <article
                key={account.id}
                className="social-tile"
                aria-label={`${platformName} account ${account.account_name}`}
              >
                <div className="social-tile-left">
                  <div
                    className="social-tile-icon"
                    style={{ background: icon.bg, color: icon.color }}
                    aria-hidden="true"
                  >
                    {icon.text}
                  </div>
                  <div className="social-tile-info">
                    <h3 className="social-tile-name">{platformName}</h3>
                    <p className="social-tile-user">{account.account_name}</p>
                    {platformDesc && <p className="social-tile-desc">{platformDesc}</p>}
                    {profileUrl && (
                      <a
                        href={profileUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="social-tile-link"
                      >
                        View Profile
                      </a>
                    )}
                  </div>
                </div>
                <div className="social-tile-right">
                  <span className={`social-status status-${status.tone}`}>
                    <span aria-hidden="true">{status.dot}</span> {status.label}
                  </span>
                  <div className="social-tile-actions">
                    {profileUrl && (
                      <a
                        href={profileUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="social-btn"
                      >
                        Manage
                      </a>
                    )}
                    <button
                      type="button"
                      onClick={() => handleDisconnect(account.id)}
                      className="social-btn danger"
                    >
                      Disconnect
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </Card>
  );
}

export default SocialAccounts;
