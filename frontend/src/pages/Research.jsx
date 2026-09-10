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
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Multi-Agent Research</h1>
          <p className="text-gray-600 mt-2">Conduct deep, evidence-backed research with AI agents</p>
        </div>

        {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          {/* Tabs */}
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px" aria-label="Tabs">
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => { setActiveTab(tab.id); setShowDetail(false); }}
                  className={`flex items-center px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? "border-blue-500 text-blue-600 bg-blue-50"
                      : "border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {/* New Research Tab */}
            {activeTab === "new" && (
              <div className="max-w-3xl mx-auto">
                <Card className="p-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-2">Start New Research</h2>
                  <p className="text-gray-600 mb-6">
                    Enter your research question and our multi-agent system will gather evidence, verify claims, and generate a comprehensive report.
                  </p>
                  
                  <form onSubmit={startResearch} className="space-y-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Research Question <span className="text-red-500">*</span>
                      </label>
                      <Textarea
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        placeholder="What would you like to research? Be specific for better results..."
                        rows={4}
                        required
                        className="w-full"
                      />
                      <p className="text-sm text-gray-500 mt-1">
                        Example: "What are the emerging trends in AI-assisted software development for 2024?"
                      </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Research Type</label>
                        <select
                          value={researchType}
                          onChange={e => setResearchType(e.target.value)}
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="general">General</option>
                          <option value="job_market">Job Market Analysis</option>
                          <option value="company">Company Analysis</option>
                          <option value="technology">Technology Trends</option>
                          <option value="career_path">Career Path Research</option>
                          <option value="skill_analysis">Skill Gap Analysis</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Max Sources</label>
                        <input
                          type="number"
                          value={maxSources}
                          onChange={e => setMaxSources(Math.min(50, Math.max(1, parseInt(e.target.value) || 1)))}
                          min="1"
                          max="50"
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Timeout (seconds)</label>
                        <input
                          type="number"
                          value={timeoutSeconds}
                          onChange={e => setTimeoutSeconds(Math.min(1800, Math.max(30, parseInt(e.target.value) || 30)))}
                          min="30"
                          max="1800"
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                    </div>

                    <div className="flex justify-end gap-4 pt-4 border-t border-gray-200">
                      <Button type="button" variant="secondary" onClick={() => setQuery("")}>
                        Clear
                      </Button>
                      <Button type="submit" loading={loading} className="w-full md:w-auto">
                        Start Research
                      </Button>
                    </div>
                  </form>
                </Card>

                {/* Research Types Info */}
                <div className="mt-8 grid gap-4 md:grid-cols-3">
                  {[
                    { title: "General", desc: "Broad research on any topic with comprehensive evidence gathering" },
                    { title: "Job Market", desc: "Analyze job market trends, salary data, and hiring patterns" },
                    { title: "Company", desc: "Deep dive into specific companies - culture, compensation, trajectory" },
                    { title: "Technology", desc: "Track technology trends, adoption curves, and emerging tools" },
                    { title: "Career Path", desc: "Map career progression paths, required skills, and transitions" },
                    { title: "Skill Analysis", desc: "Identify skill gaps and learning priorities for target roles" },
                  ].map((item, i) => (
                    <Card key={i} className="p-4 hover:shadow-md transition-shadow">
                      <h3 className="font-medium text-gray-900 mb-1">{item.title}</h3>
                      <p className="text-sm text-gray-600">{item.desc}</p>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {/* Projects Tab */}
            {activeTab === "projects" && (
              <div>
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-lg font-medium text-gray-900">Research Projects</h2>
                  <Button onClick={() => setActiveTab("new")} variant="primary">
                    New Research
                  </Button>
                </div>

                {loading && researchList.length === 0 ? (
                  <div className="text-center py-12">
                    <Loading />
                  </div>
                ) : null}

                {researchList.length === 0 && !loading && (
                  <Card className="p-8 text-center">
                    <div className="text-4xl mb-4">🔬</div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No research projects yet</h3>
                    <p className="text-gray-500 mb-6">Start your first research project to see it here</p>
                    <Button onClick={() => setActiveTab("new")} variant="primary" className="w-full md:w-auto">
                      Start Research
                    </Button>
                  </Card>
                )}

                <div className="space-y-4">
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
  const statusColors = {
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
    researching: "bg-blue-100 text-blue-800",
    planning: "bg-yellow-100 text-yellow-800",
    created: "bg-gray-100 text-gray-800",
  };

  return (
    <Card className="p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-2">
            <h3 className="font-medium text-gray-900 truncate">{research.query}</h3>
            <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusColors[research.status] || "bg-gray-100 text-gray-800"}`}>
              {research.status}
            </span>
          </div>
          <div className="flex flex-wrap gap-4 text-sm text-gray-500">
            <span className="flex items-center gap-1">📋 {research.research_type}</span>
            <span className="flex items-center gap-1">📚 {research.source_count || 0} sources</span>
            <span className="flex items-center gap-1">✅ {research.verified_claim_count || 0} verified</span>
            {research.confidence_score && (
              <span className="flex items-center gap-1">🎯 {(research.confidence_score * 100).toFixed(0)}% confidence</span>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Created: {new Date(research.created_at).toLocaleDateString()}
            {research.completed_at && ` • Completed: ${new Date(research.completed_at).toLocaleDateString()}`}
          </p>
        </div>
        <div className="flex gap-2 ml-4">
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