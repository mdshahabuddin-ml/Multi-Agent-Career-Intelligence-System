import { useState, useEffect, useCallback } from "react";
import { applicationService } from "../services";
import Card from "../components/common/Card";
import Loading from "../components/common/Loading";
import ErrorMessage from "../components/common/ErrorMessage";
import Button from "../components/common/Button";

const STATUS_OPTIONS = [
  { value: "draft", label: "Draft", tone: "muted", icon: "📝" },
  { value: "submitted", label: "Applied", tone: "blue", icon: "📤" },
  { value: "under_review", label: "Under Review", tone: "amber", icon: "👀" },
  { value: "interview_scheduled", label: "Interview Scheduled", tone: "purple", icon: "📅" },
  { value: "interview_completed", label: "Interview Done", tone: "indigo", icon: "🎙" },
  { value: "offer_received", label: "Offer Received", tone: "green", icon: "🎉" },
  { value: "offer_accepted", label: "Accepted", tone: "green", icon: "✅" },
  { value: "offer_declined", label: "Declined", tone: "orange", icon: "↩" },
  { value: "rejected", label: "Rejected", tone: "red", icon: "✕" },
  { value: "withdrawn", label: "Withdrawn", tone: "muted", icon: "➖" },
];

const STATUS_FLOW = ["draft", "submitted", "under_review", "interview_scheduled", "interview_completed", "offer_received"];

// Compact pipeline shown on every tile: Draft → Applied → Review → Interview → Offer
const PROGRESS_STAGES = [
  { key: "draft", label: "Draft" },
  { key: "submitted", label: "Applied" },
  { key: "under_review", label: "Review" },
  { key: "interview", label: "Interview" },
  { key: "offer", label: "Offer" },
];

function statusInfo(status) {
  return STATUS_OPTIONS.find(s => s.value === status) || { value: status, label: status, tone: "muted", icon: "•" };
}

// Backend uses the literal string "Unknown" when the job record is missing.
// Treat it as missing data and fall back professionally — never render it.
function realText(value) {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  return text.toLowerCase() === "unknown" ? "" : text;
}

function companyNameOf(app) {
  return realText(app.company_name) || realText(app.company) || "";
}

function jobTitleOf(app) {
  return realText(app.job_title) || realText(app.title) || realText(app.position) || "";
}

function formatAppDate(value) {
  if (!value) return "";
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function stageIndex(status) {
  switch (status) {
    case "draft": return 0;
    case "submitted": return 1;
    case "under_review": return 2;
    case "interview_scheduled":
    case "interview_completed": return 3;
    case "offer_received":
    case "offer_accepted": return 4;
    default: return -1;
  }
}

function Applications() {
  const [activeTab, setActiveTab] = useState("tracker");
  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        setStatsLoading(true);
        const data = await applicationService.getStatistics(controller.signal);
        setStats(data);
      } catch (err) {
        if (err.name === "CanceledError" || err.name === "AbortError") return;
      } finally {
        setStatsLoading(false);
      }
    }
    load();
    return () => controller.abort();
  }, []);

  const tabs = [
    { id: "tracker", label: "My Applications", icon: "📋", desc: "Tiles, filters & status" },
    { id: "add", label: "Add Application", icon: "➕", desc: "Log a new application" },
    { id: "stats", label: "Statistics", icon: "📊", desc: "Funnel & response rates" },
  ];

  return (
    <div className="page apps-page">
      {/* Header */}
      <div className="apps-head">
        <div className="apps-head-text">
          <h1>Applications</h1>
          <p>Track and manage your job applications.</p>
        </div>
        <div className="apps-ai-pill" title="Application stats are computed from your tracked applications">
          <span className="apps-ai-dot" aria-hidden="true" />
          <span className="apps-ai-text">
            <strong>Application tracking</strong>
            <small>Funnel · statuses · history</small>
          </span>
        </div>
      </div>

      {/* Quick Stats */}
      {stats && !statsLoading && (
        <div className="apps-stat-grid">
          <div className="apps-stat"><p className="apps-stat-value">{stats.total}</p><p className="apps-stat-label">Total</p></div>
          <div className="apps-stat blue"><p className="apps-stat-value">{stats.by_status?.submitted || 0}</p><p className="apps-stat-label">Applied</p></div>
          <div className="apps-stat purple"><p className="apps-stat-value">{(stats.by_status?.interview_scheduled || 0) + (stats.by_status?.interview_completed || 0)}</p><p className="apps-stat-label">Interviews</p></div>
          <div className="apps-stat green"><p className="apps-stat-value">{(stats.by_status?.offer_received || 0) + (stats.by_status?.offer_accepted || 0)}</p><p className="apps-stat-label">Offers</p></div>
          <div className="apps-stat red"><p className="apps-stat-value">{stats.by_status?.rejected || 0}</p><p className="apps-stat-label">Rejected</p></div>
        </div>
      )}

      {/* Tabs */}
      <nav className="apps-tabbar" aria-label="Application sections">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            aria-pressed={activeTab === tab.id}
            className={`apps-tabbtn ${activeTab === tab.id ? "active" : ""}`}
          >
            <span className="apps-tabicon" aria-hidden="true">{tab.icon}</span>
            <span className="apps-tabtext">
              <strong>{tab.label}</strong>
              <small>{tab.desc}</small>
            </span>
          </button>
        ))}
      </nav>

      {activeTab === "tracker" && <TrackerTab />}
      {activeTab === "add" && <AddApplicationTab onAdded={() => setActiveTab("tracker")} />}
      {activeTab === "stats" && <StatsTab />}
    </div>
  );
}

/* ============================================
   Tracker Tab
   ============================================ */

function TrackerTab() {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("all");
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ notes: "", interview_date: "" });
  const [openMenuId, setOpenMenuId] = useState(null);
  const [detailId, setDetailId] = useState(null);
  const [details, setDetails] = useState({});
  const [detailLoadingId, setDetailLoadingId] = useState(null);

  const fetchApps = useCallback(async () => {
    try {
      setLoading(true);
      const params = filter !== "all" ? { status: filter } : {};
      const data = await applicationService.getApplications(params);
      setApplications(data);
    } catch (err) {
      if (err.name === "CanceledError" || err.name === "AbortError") return;
      setError(err.response?.data?.detail || err.message || "Failed to load applications");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { fetchApps(); }, [fetchApps]);

  useEffect(() => {
    if (openMenuId === null) return;
    const close = (e) => { if (e.key === "Escape") setOpenMenuId(null); };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [openMenuId]);

  const handleStatusChange = async (appId, newStatus) => {
    setOpenMenuId(null);
    try {
      await applicationService.updateStatus(appId, newStatus);
      fetchApps();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to update status");
    }
  };

  const handleDelete = async (appId) => {
    setOpenMenuId(null);
    if (!confirm("Delete this application?")) return;
    try {
      await applicationService.deleteApplication(appId);
      fetchApps();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to delete");
    }
  };

  const startEdit = (app) => {
    setOpenMenuId(null);
    setEditingId(app.id);
    setEditForm({ notes: app.notes || "", interview_date: app.interview_date || "" });
  };

  const saveEdit = async (appId) => {
    try {
      await applicationService.updateStatus(appId, {
        status: applications.find(a => a.id === appId)?.status,
        notes: editForm.notes,
        interview_date: editForm.interview_date || undefined,
      });
      setEditingId(null);
      fetchApps();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to update");
    }
  };

  const toggleDetails = async (app) => {
    if (detailId === app.id) {
      setDetailId(null);
      return;
    }
    setDetailId(app.id);
    if (details[app.id]) return;
    setDetailLoadingId(app.id);
    try {
      const data = await applicationService.getApplication(app.id);
      setDetails(prev => ({ ...prev, [app.id]: data }));
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load application details");
      setDetailId(null);
    } finally {
      setDetailLoadingId(null);
    }
  };

  const getNextStatus = (currentStatus) => {
    const idx = STATUS_FLOW.indexOf(currentStatus);
    if (idx >= 0 && idx < STATUS_FLOW.length - 1) return STATUS_FLOW[idx + 1];
    return null;
  };

  if (loading) return <Card><Loading /></Card>;

  const filteredApps = filter === "all" ? applications : applications;

  return (
    <div className="apps-stack">
      {error && <ErrorMessage message={error} />}

      {/* Status Filter */}
      <div className="apps-filters" aria-label="Filter by status">
        <button onClick={() => setFilter("all")} aria-pressed={filter === "all"} className={`apps-filterbtn ${filter === "all" ? "active" : ""}`}>
          All <span className="apps-filtercount">({applications.length})</span>
        </button>
        {STATUS_OPTIONS.map(s => {
          const count = applications.filter(a => a.status === s.value).length;
          if (count === 0) return null;
          return (
            <button key={s.value} onClick={() => setFilter(s.value)} aria-pressed={filter === s.value} className={`apps-filterbtn ${filter === s.value ? "active" : ""}`}>
              {s.label} <span className="apps-filtercount">({count})</span>
            </button>
          );
        })}
      </div>

      {/* Applications List */}
      {filteredApps.length === 0 ? (
        <Card>
          <div className="apps-empty slim">
            <h3>{filter === "all" ? "No applications yet" : "Nothing here"}</h3>
            <p>{filter === "all" ? "Add your first application to start tracking." : `No applications with status "${filter}".`}</p>
          </div>
        </Card>
      ) : (
        <div className="apps-tiles">
          {filteredApps.map((app) => (
            <ApplicationTile
              key={app.id}
              app={app}
              editing={editingId === app.id}
              editForm={editForm}
              onEditFormChange={setEditForm}
              onStartEdit={() => startEdit(app)}
              onCancelEdit={() => setEditingId(null)}
              onSaveEdit={() => saveEdit(app.id)}
              onDelete={() => handleDelete(app.id)}
              onStatusChange={(s) => handleStatusChange(app.id, s)}
              nextStatus={getNextStatus(app.status)}
              menuOpen={openMenuId === app.id}
              onToggleMenu={() => setOpenMenuId(openMenuId === app.id ? null : app.id)}
              onCloseMenu={() => setOpenMenuId(null)}
              detailsOpen={detailId === app.id}
              details={details[app.id]}
              detailsLoading={detailLoadingId === app.id}
              onToggleDetails={() => toggleDetails(app)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/* ============================================
   Application Tile
   ============================================ */

function ApplicationTile({
  app, editing, editForm, onEditFormChange,
  onStartEdit, onCancelEdit, onSaveEdit, onDelete, onStatusChange,
  nextStatus, menuOpen, onToggleMenu, onCloseMenu,
  detailsOpen, details, detailsLoading, onToggleDetails,
}) {
  const info = statusInfo(app.status);
  const nextInfo = nextStatus ? statusInfo(nextStatus) : null;
  const company = companyNameOf(app);
  const title = jobTitleOf(app);
  const applied = formatAppDate(app.applied_date);
  const interview = formatAppDate(app.interview_date);
  const stage = stageIndex(app.status);
  const avatarLetter = (company || title).charAt(0).toUpperCase();

  return (
    <article className="app-tile">
      <div className="app-tile-top">
        <div className="app-avatar" aria-hidden="true">
          {company ? avatarLetter : "💼"}
        </div>
        <div className="app-tile-heading">
          <h3 className="app-company" title={company || "Company not specified"}>
            {company || "Company not specified"}
          </h3>
          <p className="app-title" title={title || "Position not specified"}>
            {title || (app.job_id ? `Job #${app.job_id}` : "Position not specified")}
          </p>
        </div>
        <span className={`app-status status-${info.tone}`} title={`Status: ${info.label}`}>
          <span aria-hidden="true">{info.icon}</span> {info.label}
        </span>
      </div>

      {(app.location || app.employment_type) && (
        <p className="app-meta">
          {app.location && <span>📍 {app.location}</span>}
          {app.location && app.employment_type && <span aria-hidden="true"> · </span>}
          {app.employment_type && <span>💼 {app.employment_type}</span>}
        </p>
      )}

      <p className="app-date">
        {applied ? `Applied ${applied}` : "Date not specified"}
        {interview && <span> · 🎯 Interview {interview}</span>}
      </p>

      {/* Progress */}
      <ol className="app-progress" aria-label={`Progress: ${info.label}`}>
        {PROGRESS_STAGES.map((s, i) => (
          <li key={s.key} className={`app-stage ${stage >= 0 && i < stage ? "done" : ""} ${i === stage ? "current" : ""}`}>
            <span className="app-dot" aria-hidden="true" />
            <span className="app-stage-label">{s.label}</span>
          </li>
        ))}
      </ol>

      {/* Actions */}
      <div className="app-tile-actions">
        <button type="button" className="app-btn" onClick={onToggleDetails} aria-expanded={detailsOpen}>
          {detailsOpen ? "Hide Details" : "View Details"}
        </button>
        <button type="button" className="app-btn" onClick={onStartEdit}>
          Edit
        </button>
        <div className="app-menu-wrap">
          <button
            type="button"
            className="app-btn app-menu-btn"
            onClick={onToggleMenu}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            aria-label="More actions"
          >
            ⋮
          </button>
          {menuOpen && (
            <>
              <button type="button" className="app-menu-backdrop" onClick={onCloseMenu} aria-label="Close menu" tabIndex={-1} />
              <div className="app-menu" role="menu">
                {nextInfo && (
                  <button type="button" role="menuitem" className="app-menu-item accent" onClick={() => onStatusChange(nextStatus)}>
                    → Move to {nextInfo.label}
                  </button>
                )}
                <p className="app-menu-heading">Update status</p>
                {STATUS_OPTIONS.map(s => (
                  <button
                    key={s.value}
                    type="button"
                    role="menuitemradio"
                    aria-checked={app.status === s.value}
                    className={`app-menu-item ${app.status === s.value ? "current" : ""}`}
                    onClick={() => onStatusChange(s.value)}
                  >
                    <span aria-hidden="true">{s.icon}</span> {s.label}
                  </button>
                ))}
                <div className="app-menu-divider" />
                <button type="button" role="menuitem" className="app-menu-item danger" onClick={onDelete}>
                  🗑 Delete application
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Details */}
      {detailsOpen && (
        <div className="app-details">
          {detailsLoading ? (
            <Loading message="Loading details…" />
          ) : details ? (
            <dl className="app-details-grid">
              <div><dt>Status</dt><dd>{statusInfo(details.status).label}</dd></div>
              <div><dt>Applied</dt><dd>{formatAppDate(details.applied_date) || "—"}</dd></div>
              {details.response_date && <div><dt>Response</dt><dd>{formatAppDate(details.response_date)}</dd></div>}
              {details.interview_date && <div><dt>Interview</dt><dd>{formatAppDate(details.interview_date)}</dd></div>}
              {details.notes && <div className="span-all"><dt>Notes</dt><dd>{details.notes}</dd></div>}
              {details.cover_letter && <div className="span-all"><dt>Cover letter</dt><dd className="clamp">{details.cover_letter}</dd></div>}
            </dl>
          ) : (
            <p className="app-muted">Details unavailable.</p>
          )}
        </div>
      )}

      {/* Edit Form */}
      {editing && (
        <div className="app-edit">
          <div className="app-edit-grid">
            <label className="app-edit-field">
              <span>Interview Date</span>
              <input type="date" value={editForm.interview_date} onChange={(e) => onEditFormChange({ ...editForm, interview_date: e.target.value })} />
            </label>
            <label className="app-edit-field">
              <span>Notes</span>
              <input type="text" value={editForm.notes} onChange={(e) => onEditFormChange({ ...editForm, notes: e.target.value })} placeholder="Add notes..." />
            </label>
          </div>
          <div className="app-edit-actions">
            <Button onClick={onSaveEdit}>Save</Button>
            <button type="button" className="app-btn" onClick={onCancelEdit}>Cancel</button>
          </div>
        </div>
      )}
    </article>
  );
}

/* ============================================
   Add Application Tab
   ============================================ */

function AddApplicationTab({ onAdded }) {
  const [form, setForm] = useState({
    job_id: "",
    job_title: "",
    company_name: "",
    status: "draft",
    applied_date: "",
    interview_date: "",
    notes: "",
    cover_letter: "",
    source_url: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const data = {
        job_id: form.job_id ? parseInt(form.job_id) : 0,
        resume_text: " ",
        cover_letter: form.cover_letter || undefined,
      };

      const result = await applicationService.createApplication(data);

      if (form.status !== "draft" || form.notes || form.interview_date) {
        const updateBody = {};
        if (form.status !== "draft") updateBody.status = form.status;
        if (form.notes) updateBody.notes = form.notes;
        if (form.interview_date) updateBody.interview_date = form.interview_date;
        if (form.applied_date) updateBody.applied_date = form.applied_date;
        await applicationService.updateStatus(result.id, updateBody);
      }

      setSuccess(true);
      setTimeout(() => { onAdded(); }, 1000);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to create application");
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <Card>
        <div className="apps-empty slim">
          <div className="apps-empty-icon" aria-hidden="true">✓</div>
          <h3>Application added</h3>
          <p>Application added successfully! Redirecting to tracker...</p>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Add New Application">
      {error && <ErrorMessage message={error} />}
      <form onSubmit={handleSubmit} className="apps-form">
        <div className="apps-field-grid cols-2">
          <label className="apps-field">
            <span className="apps-field-label">Job ID (from Jobs page)</span>
            <input type="number" value={form.job_id} onChange={(e) => setForm({ ...form, job_id: e.target.value })} placeholder="Enter job ID if available" />
          </label>
          <label className="apps-field">
            <span className="apps-field-label">Status</span>
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>{STATUS_OPTIONS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}</select>
          </label>
        </div>
        <div className="apps-field-grid cols-2">
          <label className="apps-field">
            <span className="apps-field-label">Applied Date</span>
            <input type="date" value={form.applied_date} onChange={(e) => setForm({ ...form, applied_date: e.target.value })} />
          </label>
          <label className="apps-field">
            <span className="apps-field-label">Interview Date</span>
            <input type="date" value={form.interview_date} onChange={(e) => setForm({ ...form, interview_date: e.target.value })} />
          </label>
        </div>
        <label className="apps-field">
          <span className="apps-field-label">Notes</span>
          <textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="Add any notes about this application..." />
        </label>
        <label className="apps-field">
          <span className="apps-field-label">Cover Letter</span>
          <textarea rows={4} value={form.cover_letter} onChange={(e) => setForm({ ...form, cover_letter: e.target.value })} placeholder="Paste your cover letter..." />
        </label>
        <div><Button type="submit" loading={submitting}>{submitting ? "Adding…" : "Add Application"}</Button></div>
      </form>
    </Card>
  );
}

/* ============================================
   Stats Tab
   ============================================ */

function StatsTab() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        setLoading(true);
        const data = await applicationService.getStatistics(controller.signal);
        setStats(data);
      } catch (err) {
        if (err.name === "CanceledError" || err.name === "AbortError") return;
        setError(err.response?.data?.detail || err.message || "Failed to load stats");
      } finally {
        setLoading(false);
      }
    }
    load();
    return () => controller.abort();
  }, []);

  if (loading) return <Card><Loading /></Card>;
  if (error) return <Card><ErrorMessage message={error} /></Card>;
  if (!stats) return <Card><div className="apps-empty slim"><p>No stats available.</p></div></Card>;

  return (
    <div className="apps-stack">
      {/* Overview */}
      <Card title="Application Overview">
        <div className="apps-overview-grid">
          <div className="apps-overview blue"><p className="apps-overview-value">{stats.total}</p><p className="apps-overview-label">Total Applications</p></div>
          <div className="apps-overview green"><p className="apps-overview-value">{(stats.response_rate * 100).toFixed(0)}%</p><p className="apps-overview-label">Response Rate</p></div>
          <div className="apps-overview purple"><p className="apps-overview-value">{(stats.interview_rate * 100).toFixed(0)}%</p><p className="apps-overview-label">Interview Rate</p></div>
          <div className="apps-overview amber"><p className="apps-overview-value">{(stats.offer_rate * 100).toFixed(0)}%</p><p className="apps-overview-label">Offer Rate</p></div>
        </div>
      </Card>

      {/* Status Breakdown */}
      {stats.by_status && Object.keys(stats.by_status).length > 0 && (
        <Card title="Status Breakdown">
          <div className="apps-bars">
            {Object.entries(stats.by_status).sort((a, b) => b[1] - a[1]).map(([status, count]) => {
              const opt = statusInfo(status);
              const pct = stats.total > 0 ? (count / stats.total) * 100 : 0;
              return (
                <div key={status} className="apps-bar-row">
                  <span className={`app-status status-${opt.tone} apps-bar-badge`}>{opt.label}</span>
                  <div className="apps-bar-track">
                    <div className="apps-bar-fill" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="apps-bar-value">{count} ({pct.toFixed(0)}%)</span>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Funnel */}
      <Card title="Application Funnel">
        <div className="apps-bars">
          {[
            { label: "Total Applications", count: stats.total, tone: "funnel-total" },
            { label: "Applied", count: stats.by_status?.submitted || 0, tone: "funnel-applied" },
            { label: "Under Review", count: stats.by_status?.under_review || 0, tone: "funnel-review" },
            { label: "Interviews", count: (stats.by_status?.interview_scheduled || 0) + (stats.by_status?.interview_completed || 0), tone: "funnel-interview" },
            { label: "Offers", count: (stats.by_status?.offer_received || 0) + (stats.by_status?.offer_accepted || 0), tone: "funnel-offer" },
          ].map((step) => {
            const pct = stats.total > 0 ? (step.count / stats.total) * 100 : 0;
            return (
              <div key={step.label} className="apps-bar-row">
                <span className="apps-bar-label">{step.label}</span>
                <div className="apps-bar-track tall">
                  <div className={`apps-bar-fill ${step.tone}`} style={{ width: `${pct}%` }} />
                </div>
                <span className="apps-bar-value">{step.count}</span>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}

export default Applications;
