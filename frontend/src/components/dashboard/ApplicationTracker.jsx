import { useEffect, useState } from "react";
import { applicationService } from "../../services";
import Card from "../common/Card";
import Loading from "../common/Loading";
import ErrorMessage from "../common/ErrorMessage";
import { formatDistanceToNow } from "date-fns";

function ApplicationTracker() {
  const [applications, setApplications] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    const controller = new AbortController();

    async function fetchApplications() {
      try {
        setLoading(true);
        const [apps, statsData] = await Promise.all([
          applicationService.getApplications({}, controller.signal),
          applicationService.getStatistics(controller.signal),
        ]);
        setApplications(apps);
        setStats(statsData);
      } catch (err) {
        if (err.name === "CanceledError" || err.name === "AbortError") return;
        const message = err.response?.data?.detail || err.message || "Failed to load applications";
        setError(message);
      } finally {
        setLoading(false);
      }
    }

    fetchApplications();
    return () => controller.abort();
  }, []);

  const filteredApps = filter === "all"
    ? applications
    : applications.filter(app => app.status === filter);

  const statusConfig = {
    submitted: { label: "Submitted", color: "bg-blue-100 text-blue-800", icon: "📤" },
    under_review: { label: "Under Review", color: "bg-yellow-100 text-yellow-800", icon: "👀" },
    interview_scheduled: { label: "Interview Scheduled", color: "bg-purple-100 text-purple-800", icon: "📅" },
    interview_completed: { label: "Interview Completed", color: "bg-indigo-100 text-indigo-800", icon: "✅" },
    offer_received: { label: "Offer Received", color: "bg-green-100 text-green-800", icon: "🎉" },
    offer_accepted: { label: "Offer Accepted", color: "bg-emerald-100 text-emerald-800", icon: "✅" },
    rejected: { label: "Rejected", color: "bg-red-100 text-red-800", icon: "❌" },
    withdrawn: { label: "Withdrawn", color: "bg-gray-100 text-gray-800", icon: "↩️" },
    draft: { label: "Draft", color: "bg-gray-100 text-gray-600", icon: "📝" },
  };

  if (loading) {
    return <Card><Loading /></Card>;
  }

  if (error) {
    return <Card><ErrorMessage message={error} /></Card>;
  }

  const statusCounts = applications.reduce((acc, app) => {
    acc[app.status] = (acc[app.status] || 0) + 1;
    return acc;
  }, {});

  return (
    <Card title="Application Tracker" className="application-tracker">
      {/* Stats Overview */}
      <div className="tracker-stats">
        <div className="stat-item">
          <span className="stat-value">{stats?.total || applications.length}</span>
          <span className="stat-label">Total Applications</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{statusCounts.interview_scheduled || 0}</span>
          <span className="stat-label">Interviews</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{stats?.by_status?.offer_received || 0}</span>
          <span className="stat-label">Offers</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">
            {stats?.response_rate !== undefined
              ? `${stats.response_rate}%`
              : stats?.response_rate !== undefined
              ? `${stats.response_rate}%`
              : "N/A"}
          </span>
          <span className="stat-label">Response Rate</span>
        </div>
      </div>

      {/* Status Filter */}
      <div className="status-filters">
        {["all", "submitted", "under_review", "interview_scheduled", "interview_completed", "offer_received", "rejected", "draft"]
          .map(status => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`filter-btn ${filter === status ? "active" : ""} ${statusConfig[status]?.color || ""}`}
            >
              {statusConfig[status]?.label || status}
              <span className="filter-count">
                {status === "all"
                  ? applications.length
                  : statusCounts[status] || 0}
              </span>
            </button>
          ))}
      </div>

      {/* Applications List */}
      <div className="applications-list">
        {filteredApps.length === 0 ? (
          <div className="empty-state">
            <p>No applications found</p>
            <p className="text-sm text-gray-500">
              {filter === "all" ? "Start applying to jobs!" : `No ${filter} applications yet`}
            </p>
          </div>
        ) : (
          filteredApps.map(app => {
            const config = statusConfig[app.status] || statusConfig.submitted;
            return (
              <div key={app.id} className="application-row">
                <div className="app-main">
                  <div className="app-info">
                    <h4 className="app-title">{app.job_title || "Unknown Role"}</h4>
                    <p className="app-company">{app.company_name || "Unknown Company"}</p>
                  </div>
                  <span className={`status-badge ${config.color}`}>
                    {config.icon} {config.label}
                  </span>
                </div>
                <div className="app-meta">
                  <span className="app-date">
                    {app.applied_date
                      ? `Applied ${formatDistanceToNow(new Date(app.applied_date), { addSuffix: true })}`
                      : "Not submitted yet"}
                  </span>
                  {app.interview_date && (
                    <span className="interview-date">
                      📅 {formatDistanceToNow(new Date(app.interview_date), { addSuffix: true })}
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}

export default ApplicationTracker;