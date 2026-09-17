import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthContext } from "../context/AuthContext";
import { researchService } from "../services";
import Button from "../components/common/Button";
import Card from "../components/common/Card";
import ErrorMessage from "../components/common/ErrorMessage";
import Loading from "../components/common/Loading";
import Textarea from "../components/common/Textarea";

function Research() {
  const { user } = useAuthContext();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("new");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [researchList, setResearchList] = useState([]);
  const [activeResearch, setActiveResearch] = useState(null);
  const [showDetail, setShowDetail] = useState(false);
  
  // New research form state
  const [query, setQuery] = useState("");
  const [researchType, setResearchType] = useState("general");
  const [maxSources, setMaxSources] = useState(10);
  const [timeoutSeconds, setTimeoutSeconds] = useState(300);

  const loadResearch = async () => {
    try {
      setLoading(true);
      const data = await researchService.listResearch();
      setResearchList(data.items || data);
    } catch (err) {
      setError("Failed to load research projects");
    } finally {
      setLoading(false);
    }
  };

  const startResearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    setError("");
    setLoading(true);
    
    try {
      const research = await researchService.startResearch({
        query,
        research_type: researchType,
        max_sources: maxSources,
        timeout_seconds: timeoutSeconds,
      });
      setResearchList(prev => [research, ...prev]);
      setActiveResearch(research);
      setShowDetail(true);
      setActiveTab("projects");
      setQuery("");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to start research");
    } finally {
      setLoading(false);
    }
  };

  const viewResearch = async (researchId) => {
    try {
      setLoading(true);
      const report = await researchService.getReport(researchId);
      setActiveResearch(report);
      setShowDetail(true);
    } catch (err) {
      setError("Failed to load research report");
    } finally {
      setLoading(false);
    }
  };

  const cancelResearch = async (researchId) => {
    if (!confirm("Cancel this research?")) return;
    
    try {
      await researchService.cancelResearch(researchId);
      loadResearch();
    } catch (err) {
      setError("Failed to cancel research");
    }
  };

  useEffect(() => {
    loadResearch();
  }, []);

  const tabs = [
    { id: "projects", label: "My Projects", icon: "📋" },
    { id: "new", label: "New Research", icon: "🔬" },
  ];

  return (
    <div className="research-page">
      <div className="research-page-inner">
        <header className="research-page-header">
          <div className="research-header-copy">
            <span className="research-eyebrow">CareerIntel AI · Research Studio</span>
            <h1>Multi-Agent Research</h1>
            <p>Conduct deep, evidence-backed research with coordinated AI agents.</p>
          </div>
          <div className="research-header-visual" aria-hidden="true">
            <span className="research-header-orbit orbit-one" />
            <span className="research-header-orbit orbit-two" />
            <span className="research-header-icon">⌘</span>
          </div>
        </header>

        {error && <div className="research-feedback" role="alert"><ErrorMessage message={error} /></div>}

        <div className="research-workspace">
          {/* Tabs */}
          <div className="research-tabs-wrap">
            <nav className="research-tabs" aria-label="Research workspace sections" role="tablist">
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => { setActiveTab(tab.id); setShowDetail(false); }}
                  className={`research-tab ${activeTab === tab.id ? "active" : ""}`}
                  role="tab"
                  aria-selected={activeTab === tab.id}
                >
                  <span className="research-tab-icon" aria-hidden="true">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="research-workspace-content">
            {/* New Research Tab */}
            {activeTab === "new" && (
              <div className="research-form-layout">
                <Card className="research-form-card">
                  <div className="research-form-intro">
                    <span className="research-form-icon" aria-hidden="true">✦</span>
                    <div>
                      <h2>Start New Research</h2>
                      <p>Enter your question and our multi-agent system will gather evidence, verify claims, and generate a comprehensive report.</p>
                    </div>
                  </div>

                  <form onSubmit={startResearch} className="research-form">
                    <div className="research-field research-question-field">
                      <div className="research-field-heading">
                        <label htmlFor="research-question">Research Question <span aria-hidden="true">*</span></label>
                        <span className="research-required-note">Required</span>
                      </div>
                      <p id="research-question-help" className="research-field-help">
                        Ask a focused question to help agents gather the most relevant evidence.
                      </p>
                      <Textarea
                        id="research-question"
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        placeholder="What would you like to research? Be specific for better results..."
                        rows={4}
                        required
                        aria-describedby="research-question-help research-question-example"
                        className="research-question-input"
                      />
                      <p id="research-question-example" className="research-example">
                        <span aria-hidden="true">✦</span> Example: “What are the emerging trends in AI-assisted software development?”
                      </p>
                    </div>

                    <div className="research-field-grid">
                      <div className="research-field">
                        <label htmlFor="research-type">Research Type</label>
                        <select
                          id="research-type"
                          value={researchType}
                          onChange={e => setResearchType(e.target.value)}
                          className="research-select"
                        >
                          <option value="general">General</option>
                          <option value="job_market">Job Market Analysis</option>
                          <option value="company">Company Analysis</option>
                          <option value="technology">Technology Trends</option>
                          <option value="career_path">Career Path Research</option>
                          <option value="skill_analysis">Skill Gap Analysis</option>
                        </select>
                      </div>
                      <div className="research-field">
                        <label htmlFor="research-max-sources">Max Sources</label>
                        <input
                          id="research-max-sources"
                          type="number"
                          value={maxSources}
                          onChange={e => setMaxSources(Math.min(50, Math.max(1, parseInt(e.target.value) || 1)))}
                          min="1"
                          max="50"
                          className="research-input"
                        />
                      </div>
                    </div>

                    <div className="research-field-grid research-settings-grid">
                      <div className="research-field">
                        <label htmlFor="research-timeout">Timeout <span className="research-label-detail">(seconds)</span></label>
                        <input
                          id="research-timeout"
                          type="number"
                          value={timeoutSeconds}
                          onChange={e => setTimeoutSeconds(Math.min(1800, Math.max(30, parseInt(e.target.value) || 30)))}
                          min="30"
                          max="1800"
                          className="research-input"
                        />
                      </div>
                    </div>

                    <div className="research-form-actions">
                      <Button type="button" variant="secondary" onClick={() => setQuery("")}>
                        Clear
                      </Button>
                      <Button type="submit" loading={loading}>
                        <span aria-hidden="true">✦</span> Start Research
                      </Button>
                    </div>
                  </form>
                </Card>

                {/* Research Types Info */}
                <div className="research-type-cards">
                  {[
                    { title: "General", desc: "Broad research on any topic with comprehensive evidence gathering" },
                    { title: "Job Market", desc: "Analyze job market trends, salary data, and hiring patterns" },
                    { title: "Company", desc: "Deep dive into specific companies - culture, compensation, trajectory" },
                    { title: "Technology", desc: "Track technology trends, adoption curves, and emerging tools" },
                    { title: "Career Path", desc: "Map career progression paths, required skills, and transitions" },
                    { title: "Skill Analysis", desc: "Identify skill gaps and learning priorities for target roles" },
                  ].map((item, i) => (
                    <Card key={i} className="research-type-card">
                      <h3>{item.title}</h3>
                      <p>{item.desc}</p>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {/* Projects Tab */}
            {activeTab === "projects" && (
              <div className="research-projects-view">
                <div className="research-projects-heading">
                  <div>
                    <span className="research-section-eyebrow">Workspace</span>
                    <h2>My Research Projects</h2>
                  </div>
                  <Button onClick={() => setActiveTab("new")} variant="primary">
                    <span aria-hidden="true">✦</span> New Research
                  </Button>
                </div>

                {loading && researchList.length === 0 ? (
                  <div className="research-projects-loading">
                    <Loading />
                  </div>
                ) : null}

                {researchList.length === 0 && !loading && (
                  <Card className="research-empty-state">
                    <div className="research-empty-icon" aria-hidden="true">⌘</div>
                    <h3>No research projects yet</h3>
                    <p>Turn a career question into an evidence-backed brief with your AI research team.</p>
                    <Button onClick={() => setActiveTab("new")} variant="primary">
                      <span aria-hidden="true">✦</span> Start Your First Research
                    </Button>
                  </Card>
                )}

                <div className="research-project-list">
                  {researchList.map(research => (
                    <ResearchCard
                      key={research.id}
                      research={research}
                      onView={() => viewResearch(research.id)}
                      onCancel={() => cancelResearch(research.id)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Research Detail Modal */}
        {showDetail && activeResearch && (
          <ResearchDetailModal
            research={activeResearch}
            onClose={() => { setShowDetail(false); setActiveResearch(null); }}
          />
        )}
      </div>
    </div>
  );
}

function ResearchCard({ research, onView, onCancel }) {
  return (
    <Card className="research-project-card">
      <div className="research-project-card-content">
        <div className="research-project-main">
          <div className="research-project-title-row">
            <h3>{research.query}</h3>
            <span className={`research-status status-${research.status}`}>
              {research.status}
            </span>
          </div>
          <div className="research-project-meta">
            <span><i aria-hidden="true">▦</i> {research.research_type}</span>
            <span><i aria-hidden="true">◫</i> {research.source_count || 0} sources</span>
            <span><i aria-hidden="true">✓</i> {research.verified_claim_count || 0} verified</span>
            {research.confidence_score && (
              <span><i aria-hidden="true">◎</i> {(research.confidence_score * 100).toFixed(0)}% confidence</span>
            )}
          </div>
          <p className="research-project-date">
            Created: {new Date(research.created_at).toLocaleDateString()}
            {research.completed_at && ` • Completed: ${new Date(research.completed_at).toLocaleDateString()}`}
          </p>
        </div>
        <div className="research-project-actions">
          <Button onClick={onView} variant="secondary" size="sm">
            {research.status === "completed" ? "View Report" : "View Progress"}
          </Button>
          {research.status === "researching" && (
            <Button onClick={() => onCancel(research.id)} variant="danger" size="sm">
              Cancel
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}

function ResearchDetailModal({ research, onClose }) {
  const statusColors = {
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
    researching: "bg-blue-100 text-blue-800",
    planning: "bg-yellow-100 text-yellow-800",
    created: "bg-gray-100 text-gray-800",
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="relative mx-auto mt-20 max-w-4xl p-6 bg-white rounded-xl shadow-xl">
        <div className="flex items-start justify-between mb-6">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h2 className="text-xl font-bold text-gray-900">{research.query}</h2>
              <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusColors[research.status] || "bg-gray-100 text-gray-800"}`}>
                {research.status}
              </span>
            </div>
            <div className="flex flex-wrap gap-4 text-sm text-gray-500">
              <span>Type: {research.research_type}</span>
              <span>Sources: {research.source_count || 0}</span>
              <span>Verified: {research.verified_claim_count || 0}</span>
              {research.confidence_score && <span>Confidence: {(research.confidence_score * 100).toFixed(0)}%</span>}
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl">×</button>
        </div>

        {research.report && (
          <div className="prose prose-gray max-w-none mb-6">
            <div className="bg-gray-50 p-4 rounded-lg">
              {research.report}
            </div>
          </div>
        )}

        {research.sources && research.sources.length > 0 && (
          <div className="mb-6">
            <h3 className="font-medium text-gray-900 mb-3">Sources</h3>
            <ul className="space-y-2">
              {research.sources.map((source, i) => (
                <li key={i} className="text-sm">
                  <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                    {source.title}
                  </a>
                  <span className="text-gray-500 ml-2">{source.source_type} • {Math.round((source.credibility_score || 0) * 100)}% credibility</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {research.citations && research.citations.length > 0 && (
          <div>
            <h3 className="font-medium text-gray-900 mb-3">Citations</h3>
            <ol className="space-y-2 list-decimal list-inside text-sm text-gray-700">
              {research.citations.map((citation, i) => (
                <li key={i} className="prose prose-sm max-w-none">
                  {citation.citation_format}
                </li>
              ))}
            </ol>
          </div>
        )}

        <div className="flex justify-end pt-4 border-t border-gray-200">
          <Button onClick={onClose} variant="secondary">Close</Button>
        </div>
      </div>
    </div>
  );
}

export default Research;
