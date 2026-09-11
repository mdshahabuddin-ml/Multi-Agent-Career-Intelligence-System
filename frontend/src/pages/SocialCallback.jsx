import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import socialService from "../services/socialService";

function SocialCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState("Processing...");
  const [error, setError] = useState(null);

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const provider = searchParams.get("provider");
    const errorParam = searchParams.get("error");

    if (errorParam) {
      setError(searchParams.get("error_description") || "Authorization failed");
      setStatus("Failed");
      return;
    }

    if (!code || !state) {
      setError("Missing authorization parameters");
      setStatus("Failed");
      return;
    }

    const completeOAuth = async () => {
      try {
        const redirectUri = `${window.location.origin}/social/callback`;
        await socialService.completeConnect(provider || "linkedin", code, state, redirectUri);
        setStatus("Connected!");
        setTimeout(() => navigate("/social"), 1500);
      } catch (err) {
        console.error("OAuth completion failed:", err);
        const msg = err.response?.data?.detail || err.message || "Connection failed";
        setError(typeof msg === "string" ? msg : JSON.stringify(msg));
        setStatus("Failed");
      }
    };

    completeOAuth();
  }, [searchParams, navigate]);

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh", background: "#f0f4f8" }}>
      <div style={{ textAlign: "center", padding: "2rem", background: "white", borderRadius: "1rem", boxShadow: "0 4px 6px rgba(0,0,0,0.1)", maxWidth: "400px", width: "100%" }}>
        {error ? (
          <>
            <div style={{ fontSize: "2rem", marginBottom: "1rem" }}>&#10060;</div>
            <h2 style={{ color: "#1e293b", marginBottom: "0.5rem" }}>Connection Failed</h2>
            <p style={{ color: "#64748b", marginBottom: "1.5rem" }}>{error}</p>
            <button
              onClick={() => navigate("/social")}
              style={{ background: "#2563eb", color: "white", border: "none", padding: "0.75rem 1.5rem", borderRadius: "0.5rem", cursor: "pointer", fontWeight: 600 }}
            >
              Back to Social
            </button>
          </>
        ) : (
          <>
            <div style={{ fontSize: "2rem", marginBottom: "1rem" }}>&#8987;</div>
            <h2 style={{ color: "#1e293b", marginBottom: "0.5rem" }}>{status}</h2>
            <p style={{ color: "#64748b" }}>
              {status === "Connected!" ? "Redirecting to Social page..." : "Please wait while we complete the connection..."}
            </p>
          </>
        )}
      </div>
    </div>
  );
}

export default SocialCallback;
