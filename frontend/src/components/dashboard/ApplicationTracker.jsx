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
    all: { label: "All", icon: "▦" },
    submitted: { label: "Submitted", icon: "📤" },
    under_review: { label: "Under Review", icon: "👀" },
    interview_scheduled: { label: "Interview Scheduled", icon: "📅" },
    interview_completed: { label: "Interview Completed", icon: "✅" },
    offer_received: { label: "Offer Received", icon: "🎉" },
    offer_accepted: { label: "Offer Accepted", icon: "✅" },
    rejected: { label: "Rejected", icon: "❌" },
    withdrawn: { label: "Withdrawn", icon: "↩️" },
    draft: { label: "Draft", icon: "📝" },
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

  const trackerMetrics = [
    { label: "Total Applications", value: stats?.total ?? applications.length, icon: "▦", tone: "primary" },
    { label: "Interviews", value: statusCounts.interview_scheduled || 0, icon: "◌", tone: "violet" },
    { label: "Offers", value: stats?.by_status?.offer_received || 0, icon: "✦", tone: "success" },
    { label: "Response Rate", value: stats?.response_rate !== undefined ? `${stats.response_rate}%` : "N/A", icon: "%", tone: "amber" },
  ];

  return (
    <Card title="Application Tracker" className="application-tracker">
      <div className="tracker-stats">
        {trackerMetrics.map((metric) => (
          <div key={metric.label} className={`tracker-stat tracker-stat-${metric.tone}`}>
            <span className="tracker-stat-icon" aria-hidden="true">{metric.icon}</span>
            <div className="tracker-stat-content">
              <span className="tracker-stat-value">{metric.value}</span>
              <span className="tracker-stat-label">{metric.label}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="tracker-filter-group">
        <p className="tracker-filter-label">Filter applications</p>
        <div className="status-filters" aria-label="Filter applications by status">
        {["all", "submitted", "under_review", "interview_scheduled", "interview_completed", "offer_received", "rejected", "draft"]
          .map(status => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`filter-btn ${filter === status ? "active" : ""}`}
              aria-pressed={filter === status}
              data-status={status}
            >
              <span>{statusConfig[status]?.label || status}</span>
              <span className="filter-count">
                {status === "all"
                  ? applications.length
                  : statusCounts[status] || 0}
              </span>
            </button>
          ))}
        </div>
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
                  <span className={`application-status status-${app.status}`}>
                    <span aria-hidden="true">{config.icon}</span> {config.label}
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
