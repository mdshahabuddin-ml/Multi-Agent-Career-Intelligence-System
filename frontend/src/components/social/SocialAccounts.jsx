import { useState, useEffect } from "react";
import socialService from "../../services/socialService";
import Card from "../common/Card";
import Loading from "../common/Loading";

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

  if (loading) return <Loading />;

  return (
    <Card title="Social Accounts">
      {accounts.length === 0 ? (
        <p style={{ color: "#6b7280", textAlign: "center", padding: "1rem 0" }}>No accounts connected</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {accounts.map((account) => {
            const icon = getPlatformIcon(account.platform);
            const profileUrl = getProfileUrl(account);
            return (
              <div
                key={account.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "0.75rem",
                  border: "1px solid #e5e7eb",
                  borderRadius: "0.5rem",
                  background: "#f9fafb"
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <div style={{
                    width: "40px",
                    height: "40px",
                    borderRadius: "0.5rem",
                    background: icon.bg,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: icon.color,
                    fontWeight: 700,
                    fontSize: "0.875rem"
                  }}>
                    {icon.text}
                  </div>
                  <div>
                    <p style={{ fontWeight: 600, color: "#111827", margin: 0 }}>
                      {account.platform.charAt(0).toUpperCase() + account.platform.slice(1)}
                    </p>
                    <p style={{ fontSize: "0.875rem", color: "#6b7280", margin: 0 }}>
                      {account.account_name}
                    </p>
                    {profileUrl && (
                      <a
                        href={profileUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ fontSize: "0.75rem", color: "#2563eb", textDecoration: "none" }}
                      >
                        View Profile
                      </a>
                    )}
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span style={{
                    padding: "0.25rem 0.5rem",
                    fontSize: "0.75rem",
                    background: "#dcfce7",
                    color: "#166534",
                    borderRadius: "9999px",
                    fontWeight: 500
                  }}>
                    Connected
                  </span>
                  <button
                    onClick={() => handleDisconnect(account.id)}
                    style={{
                      padding: "0.25rem 0.5rem",
                      fontSize: "0.75rem",
                      background: "#fee2e2",
                      color: "#991b1b",
                      border: "none",
                      borderRadius: "0.25rem",
                      cursor: "pointer"
                    }}
                  >
                    Disconnect
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

export default SocialAccounts;
