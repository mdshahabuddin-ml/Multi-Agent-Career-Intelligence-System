import { useState, useEffect, useCallback } from "react";
import { applicationService, jobService } from "../services";
import Card from "../components/common/Card";
import Loading from "../components/common/Loading";
import ErrorMessage from "../components/common/ErrorMessage";
import Button from "../components/common/Button";

const STATUS_OPTIONS = [
  { value: "draft", label: "Draft", color: "bg-gray-100 text-gray-700" },
  { value: "submitted", label: "Applied", color: "bg-blue-100 text-blue-700" },
  { value: "under_review", label: "Under Review", color: "bg-yellow-100 text-yellow-700" },
  { value: "interview_scheduled", label: "Interview Scheduled", color: "bg-purple-100 text-purple-700" },
  { value: "interview_completed", label: "Interview Done", color: "bg-indigo-100 text-indigo-700" },
  { value: "offer_received", label: "Offer Received", color: "bg-green-100 text-green-700" },
  { value: "offer_accepted", label: "Accepted", color: "bg-green-200 text-green-800" },
  { value: "offer_declined", label: "Declined", color: "bg-orange-100 text-orange-700" },
  { value: "rejected", label: "Rejected", color: "bg-red-100 text-red-700" },
  { value: "withdrawn", label: "Withdrawn", color: "bg-gray-100 text-gray-500" },
];

const STATUS_FLOW = ["draft", "submitted", "under_review", "interview_scheduled", "interview_completed", "offer_received"];

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
    { id: "tracker", label: "My Applications", icon: "📋" },
    { id: "add", label: "Add Application", icon: "➕" },
    { id: "stats", label: "Statistics", icon: "📊" },
  ];

  return (
    <div className="page">
      <div className="page-header">
        <h1>Applications</h1>
        <p>Track and manage your job applications</p>
      </div>

      {/* Quick Stats */}
      {stats && !statsLoading && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 mb-6">
          <Card><div className="text-center"><p className="text-2xl font-bold text-gray-900">{stats.total}</p><p className="text-xs text-gray-500">Total</p></div></Card>
          <Card><div className="text-center"><p className="text-2xl font-bold text-blue-600">{stats.by_status?.submitted || 0}</p><p className="text-xs text-gray-500">Applied</p></div></Card>
          <Card><div className="text-center"><p className="text-2xl font-bold text-purple-600">{(stats.by_status?.interview_scheduled || 0) + (stats.by_status?.interview_completed || 0)}</p><p className="text-xs text-gray-500">Interviews</p></div></Card>
          <Card><div className="text-center"><p className="text-2xl font-bold text-green-600">{(stats.by_status?.offer_received || 0) + (stats.by_status?.offer_accepted || 0)}</p><p className="text-xs text-gray-500">Offers</p></div></Card>
          <Card><div className="text-center"><p className="text-2xl font-bold text-red-600">{stats.by_status?.rejected || 0}</p><p className="text-xs text-gray-500">Rejected</p></div></Card>
        </div>
      )}

      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-1 -mb-px overflow-x-auto">
          {tabs.map((tab) => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${activeTab === tab.id ? "border-blue-500 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"}`}>
              <span className="mr-1">{tab.icon}</span>{tab.label}
            </button>
          ))}
        </nav>
      </div>

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

  const handleStatusChange = async (appId, newStatus) => {
    try {
      await applicationService.updateStatus(appId, newStatus);
      fetchApps();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to update status");
    }
  };

  const handleDelete = async (appId) => {
    if (!confirm("Delete this application?")) return;
    try {
      await applicationService.deleteApplication(appId);
      fetchApps();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to delete");
    }
  };

  const startEdit = (app) => {
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

  const getNextStatus = (currentStatus) => {
    const idx = STATUS_FLOW.indexOf(currentStatus);
    if (idx >= 0 && idx < STATUS_FLOW.length - 1) return STATUS_FLOW[idx + 1];
    return null;
  };

  if (loading) return <Card><Loading /></Card>;

  const filteredApps = filter === "all" ? applications : applications;

  return (
    <div className="space-y-6">
      {error && <ErrorMessage message={error} />}

      {/* Status Filter */}
      <div className="flex flex-wrap gap-2">
        <button onClick={() => setFilter("all")} className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${filter === "all" ? "bg-blue-100 text-blue-700 border-blue-300" : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"}`}>
          All ({applications.length})
        </button>
        {STATUS_OPTIONS.map(s => {
          const count = applications.filter(a => a.status === s.value).length;
          if (count === 0) return null;
          return (
            <button key={s.value} onClick={() => setFilter(s.value)} className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${filter === s.value ? `${s.color} border-current` : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"}`}>
              {s.label} ({count})
            </button>
          );
        })}
      </div>

      {/* Applications List */}
      {filteredApps.length === 0 ? (
        <Card>
          <p className="text-gray-500 text-center py-8">
            {filter === "all" ? "No applications yet. Add your first application to start tracking." : `No applications with status "${filter}".`}
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredApps.map((app) => {
            const statusOpt = STATUS_OPTIONS.find(s => s.value === app.status) || STATUS_OPTIONS[0];
            const nextStatus = getNextStatus(app.status);
            const nextStatusOpt = nextStatus ? STATUS_OPTIONS.find(s => s.value === nextStatus) : null;

            return (
              <Card key={app.id}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-medium text-gray-900 truncate">{app.job_title || `Job #${app.job_id}`}</h3>
                      <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusOpt.color}`}>{statusOpt.label}</span>
                    </div>
                    <p className="text-sm text-gray-600 mt-0.5">{app.company_name || "Unknown Company"}</p>
                    <div className="flex flex-wrap gap-3 mt-1 text-xs text-gray-500">
                      {app.applied_date && <span>Applied: {new Date(app.applied_date).toLocaleDateString()}</span>}
                      {app.interview_date && <span>Interview: {new Date(app.interview_date).toLocaleDateString()}</span>}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    {nextStatusOpt && (
                      <button onClick={() => handleStatusChange(app.id, nextStatus)} className="px-3 py-1 text-xs font-medium bg-green-50 text-green-700 border border-green-200 rounded-lg hover:bg-green-100 transition-colors">
                        → {nextStatusOpt.label}
                      </button>
                    )}
                    <button onClick={() => startEdit(app)} className="px-2 py-1 text-xs text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50">Edit</button>
                    <button onClick={() => handleDelete(app.id)} className="px-2 py-1 text-xs text-red-500 hover:text-red-700 border border-red-200 rounded-lg hover:bg-red-50">Delete</button>
                  </div>
                </div>

                {/* Edit Form */}
                {editingId === app.id && (
                  <div className="mt-4 pt-4 border-t border-gray-200 space-y-3">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">Interview Date</label>
                        <input type="date" value={editForm.interview_date} onChange={(e) => setEditForm({ ...editForm, interview_date: e.target.value })} className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">Notes</label>
                        <input type="text" value={editForm.notes} onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })} className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="Add notes..." />
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button onClick={() => saveEdit(app.id)} className="text-xs py-1">Save</Button>
                      <button onClick={() => setEditingId(null)} className="px-3 py-1 text-xs text-gray-500 hover:text-gray-700">Cancel</button>
                    </div>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
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
    return <Card><div className="text-center py-8"><p className="text-green-600 font-medium">Application added successfully!</p><p className="text-sm text-gray-500 mt-1">Redirecting to tracker...</p></div></Card>;
  }

  return (
    <Card title="Add New Application">
      {error && <ErrorMessage message={error} />}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div><label className="block text-sm font-medium text-gray-700 mb-1">Job ID (from Jobs page)</label><input type="number" value={form.job_id} onChange={(e) => setForm({ ...form, job_id: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="Enter job ID if available" /></div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">Status</label><select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">{STATUS_OPTIONS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}</select></div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div><label className="block text-sm font-medium text-gray-700 mb-1">Applied Date</label><input type="date" value={form.applied_date} onChange={(e) => setForm({ ...form, applied_date: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" /></div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">Interview Date</label><input type="date" value={form.interview_date} onChange={(e) => setForm({ ...form, interview_date: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" /></div>
        </div>
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Notes</label><textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 resize-y" placeholder="Add any notes about this application..." /></div>
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Cover Letter</label><textarea rows={4} value={form.cover_letter} onChange={(e) => setForm({ ...form, cover_letter: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 resize-y" placeholder="Paste your cover letter..." /></div>
        <Button type="submit" loading={submitting}>Add Application</Button>
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
  if (!stats) return <Card><p className="text-gray-500">No stats available.</p></Card>;

  return (
    <div className="space-y-6">
      {/* Overview */}
      <Card title="Application Overview">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-blue-50 rounded-lg"><p className="text-3xl font-bold text-blue-700">{stats.total}</p><p className="text-sm text-gray-500">Total Applications</p></div>
          <div className="text-center p-4 bg-green-50 rounded-lg"><p className="text-3xl font-bold text-green-700">{(stats.response_rate * 100).toFixed(0)}%</p><p className="text-sm text-gray-500">Response Rate</p></div>
          <div className="text-center p-4 bg-purple-50 rounded-lg"><p className="text-3xl font-bold text-purple-700">{(stats.interview_rate * 100).toFixed(0)}%</p><p className="text-sm text-gray-500">Interview Rate</p></div>
          <div className="text-center p-4 bg-yellow-50 rounded-lg"><p className="text-3xl font-bold text-yellow-700">{(stats.offer_rate * 100).toFixed(0)}%</p><p className="text-sm text-gray-500">Offer Rate</p></div>
        </div>
      </Card>

      {/* Status Breakdown */}
      {stats.by_status && Object.keys(stats.by_status).length > 0 && (
        <Card title="Status Breakdown">
          <div className="space-y-3">
            {Object.entries(stats.by_status).sort((a, b) => b[1] - a[1]).map(([status, count]) => {
              const statusOpt = STATUS_OPTIONS.find(s => s.value === status) || { label: status, color: "bg-gray-100 text-gray-700" };
              const pct = stats.total > 0 ? (count / stats.total) * 100 : 0;
              return (
                <div key={status} className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusOpt.color} w-36 text-center`}>{statusOpt.label}</span>
                  <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-sm text-gray-500 w-16 text-right">{count} ({pct.toFixed(0)}%)</span>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Funnel */}
      <Card title="Application Funnel">
        <div className="space-y-2">
          {[
            { label: "Total Applications", count: stats.total, color: "bg-blue-500" },
            { label: "Applied", count: stats.by_status?.submitted || 0, color: "bg-blue-400" },
            { label: "Under Review", count: stats.by_status?.under_review || 0, color: "bg-yellow-400" },
            { label: "Interviews", count: (stats.by_status?.interview_scheduled || 0) + (stats.by_status?.interview_completed || 0), color: "bg-purple-400" },
            { label: "Offers", count: (stats.by_status?.offer_received || 0) + (stats.by_status?.offer_accepted || 0), color: "bg-green-400" },
          ].map((step, i) => {
            const pct = stats.total > 0 ? (step.count / stats.total) * 100 : 0;
            return (
              <div key={i} className="flex items-center gap-3">
                <span className="text-sm text-gray-700 w-40">{step.label}</span>
                <div className="flex-1 h-4 bg-gray-100 rounded overflow-hidden">
                  <div className={`h-full ${step.color} rounded`} style={{ width: `${pct}%` }} />
                </div>
                <span className="text-sm text-gray-500 w-20 text-right">{step.count}</span>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}

export default Applications;
