import { useEffect, useState } from "react";
import { researchService } from "../../services";
import Card from "../common/Card";
import Loading from "../common/Loading";
import ErrorMessage from "../common/ErrorMessage";

function ResearchPanel() {
  const [researchList, setResearchList] = useState([]);
  const [activeResearch, setActiveResearch] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showDetail, setShowDetail] = useState(false);

  useEffect(() => {
    loadResearch();
  }, []);

  const loadResearch = async () => {
    try {
      setLoading(true);
      const data = await researchService.listResearch();
      setResearchList(data);
    } catch (err) {
      setError("Failed to load research");
    } finally {
      setLoading(false);
    }
  };

  const startResearch = async (query, researchType) => {
    try {
      setLoading(true);
      const research = await researchService.startResearch({
        query,
        research_type: researchType,
      });
      setResearchList(prev => [research, ...prev]);
      setActiveResearch(research);
      setShowDetail(true);
    } catch (err) {
      setError("Failed to start research");
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
    try {
      await researchService.cancelResearch(researchId);
      loadResearch();
    } catch (err) {
      setError("Failed to cancel research");
    }
  };

  if (loading && !activeResearch) {
    return <Card><Loading /></Card>;
  }

  if (error) {
    return <Card><ErrorMessage message={error} /></Card>;
  }

  return (
    <Card title="Research Intelligence" className="research-panel">
      <div className="research-header">
        <h3>Multi-Agent Research</h3>
        <div className="research-actions">
          <button className="btn btn-primary btn-sm" onClick={() => showNewResearchModal()}>
            New Research
          </button>
        </div>
      </div>

      {showDetail && activeResearch && (
        <ResearchDetailView
          research={activeResearch}
          onClose={() => setShowDetail(false)}
        />
      )}

      <div className="research-list">
        {researchList.length === 0 ? (
          <div className="empty-state">
            <p>No research projects yet</p>
            <button className="btn btn-primary btn-sm" onClick={() => showNewResearchModal()}>
              Start Your First Research
            </button>
          </div>
        ) : (
          <>
            {researchList.map(research => (
              <ResearchCard
                key={research.id}
                research={research}
                onView={() => viewResearch(research.id)}
                onCancel={() => cancelResearch(research.id)}
              />
            ))}
          </>
        )}
      </div>
    </Card>
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
    <div className="research-card">
      <div className="research-header">
        <h4>{research.query}</h4>
        <span className={`status-badge ${statusColors[research.status] || "bg-gray-100 text-gray-800"}`}>
          {research.status}
        </span>
      </div>
      <div className="research-meta">
        <span className="meta-item">
          <span className="meta-label">Type:</span>
          <span className="meta-value">{research.research_type}</span>
        </span>
        <span className="meta-item">
          <span className="meta-label">Sources:</span>
          <span className="meta-value">{research.source_count}</span>
        </span>
        <span className="meta-item">
          <span className="meta-label">Claims Verified:</span>
          <span className="meta-value">{research.verified_claim_count}</span>
        </span>
        <span className="meta-item">
          <span className="meta-label">Confidence:</span>
          <span className="meta-value">{research.confidence_score ? (research.confidence_score * 100).toFixed(0) + '%' : 'N/A'}</span>
        </span>
      </div>
      <div className="research-actions">
        <button className="btn btn-secondary btn-sm" onClick={() => onView(research.id)}>
          View Report
        </button>
        {research.status === "researching" && (
          <button className="btn btn-danger btn-sm" onClick={() => onCancel(research.id)}>
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}

function ResearchDetailView({ research, onClose }) {
  return (
    <div className="research-detail-modal">
      <div className="modal-overlay" onClick={onClose} />
      <div className="modal-content">
        <div className="modal-header">
          <h3>{research.query}</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          {research.report && (
            <div className="report-content" dangerouslySetInnerHTML={{ __html: research.report }} />
          )}
{research.sources && research.sources.length > 0 && (() => {
            const sourceItems = research.sources.map((source, i) => (
              <li key={i}>
                <a href={source.url} target="_blank" rel="noopener noreferrer">
                  {source.title}
                </a>
                <span className="source-meta">{source.source_type} • {source.credibility_score * 100}% credibility</span>
              </li>
            ));
            return (
              <div className="sources-section">
                <h4>Sources</h4>
                <ul className="sources-list">
                  {sourceItems}
                </ul>
              </div>
            );
          })()}
          {research.citations && research.citations.length > 0 && (
            <div className="citations-section">
              <h4>Citations</h4>
              <ol className="citations-list">
                {research.citations.map((citation, i) => (
                  <li key={i} dangerouslySetInnerHTML={{ __html: citation.citation_format }} />
                ))}
              </ol>
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn btn-primary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

function NewResearchModal({ onClose, onStart }) {
  const [query, setQuery] = useState("");
  const [type, setType] = useState("general");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onStart(query, type);
      onClose();
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Start New Research</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Research Question</label>
            <textarea
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="What would you like to research?"
              rows={3}
              required
            />
          </div>
          <div className="form-group">
            <label>Research Type</label>
            <select value={type} onChange={e => setType(e.target.value)}>
              <option value="general">General</option>
              <option value="job_market">Job Market</option>
              <option value="company">Company Analysis</option>
              <option value="technology">Technology Trends</option>
              <option value="career_path">Career Path</option>
              <option value="skill_analysis">Skill Analysis</option>
            </select>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary">Start Research</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function showNewResearchModal() {
  // This would typically use a modal state management system
  // For now, we'll just show an alert
  alert("New research modal would open here");
}

export default ResearchPanel;