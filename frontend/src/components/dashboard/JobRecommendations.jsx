import { useEffect, useState } from "react";
import { jobSearchService } from "../../services";
import Card from "../common/Card";
import Loading from "../common/Loading";
import ErrorMessage from "../common/ErrorMessage";

function JobRecommendations() {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [filters, setFilters] = useState({
    location: "",
    remote: false,
    experience_level: "",
    salary_min: "",
  });

  useEffect(() => {
    loadRecommendations();
  }, []);

  const loadRecommendations = async (append = false) => {
    try {
      setLoading(true);
      const data = await jobSearchService.getRecommendations({
        ...filters,
        page,
        limit: 10,
      });
      if (append) {
        setRecommendations(prev => [...prev, ...data.recommendations]);
      } else {
        setRecommendations(data.recommendations);
      }
      setHasMore(data.recommendations.length >= 10);
    } catch (err) {
      setError("Failed to load recommendations");
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const loadMore = () => {
    if (!loading && hasMore) {
      setPage(p => p + 1);
    }
  };

  return (
    <Card title="Job Recommendations" className="job-recommendations">
      {/* Filters */}
      <div className="recommendations-filters">
        <div className="filter-row">
          <input
            type="text"
            placeholder="Location"
            value={filters.location}
            onChange={e => handleFilterChange("location", e.target.value)}
            className="filter-input"
            placeholder="Location"
          />
          <select
            value={filters.experience_level}
            onChange={e => handleFilterChange("experience_level", e.target.value)}
            className="filter-select"
          >
            <option value="">All Levels</option>
            <option value="entry">Entry</option>
            <option value="junior">Junior</option>
            <option value="mid">Mid</option>
            <option value="senior">Senior</option>
            <option value="lead">Lead</option>
            <option value="principal">Principal</option>
          </select>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={filters.remote}
              onChange={e => handleFilterChange("remote", e.target.checked)}
            />
            Remote Only
          </label>
          <input
            type="number"
            placeholder="Min Salary"
            value={filters.salary_min}
            onChange={e => handleFilterChange("salary_min", e.target.value)}
            className="filter-input"
            placeholder="Min Salary"
          />
        </div>
      </div>

      {loading && <Loading />}

      {error && <ErrorMessage message={error} />}

      <div className="jobs-grid">
        {recommendations.map(job => (
          <JobRecommendationCard key={job.job_id} job={job} />
        ))}
      </div>

      {hasMore && (
        <div className="load-more">
          <button onClick={loadMore} disabled={loading}>
            Load More
          </button>
        </div>
      )}
    </Card>
  );
}

function JobRecommendationCard({ job }) {
  const matchScore = job.match_score || 0;
  const tier = job.tier || "fair";
  const tierColors = {
    excellent: "bg-emerald-100 text-emerald-800",
    good: "bg-green-100 text-green-800",
    fair: "bg-yellow-100 text-yellow-800",
    poor: "bg-red-100 text-red-800",
  };

  return (
    <div className="job-recommendation-card">
      <div className="job-header">
        <div className="job-title-section">
          <h3 className="job-title">{job.title}</h3>
          <p className="job-company">{job.company}</p>
        </div>
        <div className="job-meta">
          <span className={`tier-badge ${tierColors[job.tier] || tierColors.fair}`}>
            {job.tier}
          </span>
          <span className="match-score">
            {job.match_score}% Match
          </span>
        </div>
      </div>

      <div className="job-details">
        <div className="job-detail">
          <span className="detail-icon">📍</span>
          <span>{job.location || "Remote"}</span>
        </div>
        {job.salary_min && job.salary_max && (
          <div className="job-detail">
            <span className="detail-icon">💰</span>
            <span>${(job.salary_min / 1000).toFixed(0)}k - ${(job.salary_max / 1000).toFixed(0)}k</span>
          </div>
        )}
        <div className="job-detail">
          <span className="detail-icon">📊</span>
          <span>{job.experience_level || "Mid"} Level</span>
        </div>
        <div className="job-detail">
          <span className="detail-icon">🏢</span>
          <span>{job.employment_type || "Full-time"}</span>
        </div>
      </div>

      <div className="job-highlights">
        {job.highlights?.slice(0, 3).map((highlight, i) => (
          <span key={i} className="highlight-tag">{highlight}</span>
        ))}
      </div>

      {job.matching_skills?.length > 0 && (
        <div className="matching-skills">
          <span className="skills-label">Matching:</span>
          <div className="skills-tags">
            {job.matching_skills.slice(0, 4).map((skill, i) => (
              <span key={i} className="skill-tag match">{skill.skill}</span>
            ))}
          </div>
        </div>
      )}

      {job.missing_skills?.length > 0 && (
        <div className="missing-skills">
          <span className="skills-label">Missing:</span>
          <div className="skills-tags">
            {job.missing_skills.slice(0, 3).map((skill, i) => (
              <span key={i} className="skill-tag missing">{skill}</span>
            ))}
          </div>
        </div>
      )}

      <div className="job-actions">
        <button className="btn btn-primary btn-sm">
          View Details
        </button>
        <button className="btn btn-secondary btn-sm">
          Save
        </button>
      </div>
    </div>
  );
}

export default JobRecommendations;