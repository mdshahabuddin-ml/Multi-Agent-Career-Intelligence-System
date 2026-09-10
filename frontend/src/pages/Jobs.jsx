import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthContext } from "../context/AuthContext";
import { jobService, jobSearchService } from "../services";
import Button from "../components/common/Button";
import Card from "../components/common/Card";
import ErrorMessage from "../components/common/ErrorMessage";
import Loading from "../components/common/Loading";

function Jobs() {
  const { user } = useAuthContext();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("search");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Search state
  const [jobs, setJobs] = useState([]);
  const [searchParams, setSearchParams] = useState({
    query: "",
    location: "",
    remote: false,
    experience_level: "",
    salary_min: "",
    page: 1,
    limit: 20,
  });
  const [hasMore, setHasMore] = useState(true);
  const [totalJobs, setTotalJobs] = useState(0);

  // Recommendations state
  const [recommendations, setRecommendations] = useState([]);
  const [recLoading, setRecLoading] = useState(false);
  const [recPage, setRecPage] = useState(1);
  const [recHasMore, setRecHasMore] = useState(true);

  // Saved jobs
  const [savedJobs, setSavedJobs] = useState([]);

  const searchParamsRef = useRef(searchParams);
  searchParamsRef.current = searchParams;

  const loadJobs = useCallback(async (append = false, signal, overridePage) => {
    const params = searchParamsRef.current;
    setError("");
    setLoading(true);

    try {
      const response = await jobSearchService.searchJobs({
        ...params,
        page: overridePage ?? (append ? params.page : 1),
      }, signal);

      const newJobs = response.data.jobs || response.data;
      const total = response.data.total || newJobs.length;

      if (append) {
        setJobs(prev => [...prev, ...newJobs]);
      } else {
        setJobs(newJobs);
      }
      setTotalJobs(total);
      setHasMore(newJobs.length >= params.limit);
      if (!append) setSearchParams(prev => ({ ...prev, page: 1 }));
    } catch (err) {
      if (err.name === "CanceledError" || err.name === "AbortError") return;
      const message = err.response?.data?.detail || err.message || "Search failed";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadRecommendations = useCallback(async (append = false, signal) => {
    setRecLoading(true);

    try {
      const response = await jobSearchService.getRecommendations({
        page: append ? recPage : 1,
        limit: 10,
      }, signal);

      const newRecs = response.data.recommendations || response.data;

      if (append) {
        setRecommendations(prev => [...prev, ...newRecs]);
      } else {
        setRecommendations(newRecs);
      }
      setRecHasMore(newRecs.length >= 10);
      if (!append) setRecPage(1);
    } catch (err) {
      if (err.name === "CanceledError" || err.name === "AbortError") return;
      const message = err.response?.data?.detail || err.message || "Failed to load recommendations";
      console.error("Failed to load recommendations:", err);
      setError(message);
    } finally {
      setRecLoading(false);
    }
  }, [recPage]);

  const loadSavedJobs = useCallback(async (signal) => {
    try {
      const response = await jobService.getSavedJobs(signal);
      setSavedJobs(response.data);
    } catch (err) {
      if (err.name === "CanceledError" || err.name === "AbortError") return;
      const message = err.response?.data?.detail || err.message || "Failed to load saved jobs";
      console.error("Failed to load saved jobs:", err);
      setError(message);
    }
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    setSearchParams(prev => ({ ...prev, page: 1 }));
    loadJobs(false);
  };

  const handleFilterChange = (key, value) => {
    setSearchParams(prev => ({ ...prev, [key]: value, page: 1 }));
  };

  const loadMoreJobs = () => {
    if (!loading && hasMore) {
      const newPage = searchParamsRef.current.page + 1;
      setSearchParams(prev => ({ ...prev, page: newPage }));
      loadJobs(true, undefined, newPage);
    }
  };

  const loadMoreRecommendations = () => {
    if (!recLoading && recHasMore) {
      setRecPage(prev => prev + 1);
      loadRecommendations(true);
    }
  };

  const handleSaveJob = async (jobId) => {
    try {
      await jobService.saveJob(jobId);
      setJobs(prev => prev.map(job =>
        job.id === jobId ? { ...job, saved: true } : job
      ));
      loadSavedJobs();
    } catch (err) {
      const message = err.response?.data?.detail || err.message || "Failed to save job";
      setError(message);
    }
  };

  const handleUnsaveJob = async (jobId) => {
    try {
      await jobService.unsaveJob(jobId);
      setJobs(prev => prev.map(job =>
        job.id === jobId ? { ...job, saved: false } : job
      ));
      setSavedJobs(prev => prev.filter(job => job.id !== jobId));
    } catch (err) {
      const message = err.response?.data?.detail || err.message || "Failed to unsave job";
      setError(message);
    }
  };

  const handleApply = (jobId) => {
    navigate(`/jobs/${jobId}/apply`);
  };

  const handleViewDetails = (jobId) => {
    navigate(`/jobs/${jobId}`);
  };

  useEffect(() => {
    const controller = new AbortController();
    loadJobs(false, controller.signal);
    return () => controller.abort();
  }, [loadJobs]);

  useEffect(() => {
    if (activeTab === "recommendations") {
      const controller = new AbortController();
      loadRecommendations(false, controller.signal);
      return () => controller.abort();
    }
  }, [activeTab, loadRecommendations]);

  useEffect(() => {
    if (activeTab === "saved") {
      const controller = new AbortController();
      loadSavedJobs(controller.signal);
      return () => controller.abort();
    }
  }, [activeTab, loadSavedJobs]);

  const tabs = [
    { id: "search", label: "Search Jobs" },
    { id: "recommendations", label: "For You" },
    { id: "saved", label: "Saved" },
  ];

  return (
    <div className="page">
      <div className="page-header">
        <h1>Job Opportunities</h1>
        <p>Discover and match with relevant job opportunities</p>
      </div>

      {error && <ErrorMessage message={error} />}

      <Card>
        {/* Tabs */}
        <div className="jobs-tabs">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`jobs-tab ${activeTab === tab.id ? "active" : ""}`}
            >
              {tab.label}
              {tab.id === "saved" && savedJobs.length > 0 && (
                <span className="jobs-tab-badge">{savedJobs.length}</span>
              )}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="card-body">
          {/* Search Tab */}
          {activeTab === "search" && (
            <div>
              <Card title="Search Filters">
                <form onSubmit={handleSearch}>
                  <div className="form-grid">
                    <label>
                      Keywords
                      <input
                        value={searchParams.query}
                        onChange={e => handleFilterChange("query", e.target.value)}
                        placeholder="Job title, skills, company..."
                      />
                    </label>
                    <label>
                      Location
                      <input
                        value={searchParams.location}
                        onChange={e => handleFilterChange("location", e.target.value)}
                        placeholder="City, state, or Remote"
                      />
                    </label>
                    <label>
                      Experience Level
                      <select
                        value={searchParams.experience_level}
                        onChange={e => handleFilterChange("experience_level", e.target.value)}
                      >
                        <option value="">All Levels</option>
                        <option value="entry">Entry</option>
                        <option value="junior">Junior</option>
                        <option value="mid">Mid</option>
                        <option value="senior">Senior</option>
                        <option value="lead">Lead</option>
                        <option value="principal">Principal</option>
                      </select>
                    </label>
                    <label>
                      Min Salary
                      <input
                        type="number"
                        value={searchParams.salary_min}
                        onChange={e => handleFilterChange("salary_min", e.target.value)}
                        placeholder="50000"
                      />
                    </label>
                  </div>

                  <div className="jobs-filter-row">
                    <label className="jobs-checkbox">
                      <input
                        type="checkbox"
                        checked={searchParams.remote}
                        onChange={e => handleFilterChange("remote", e.target.checked)}
                      />
                      Remote Only
                    </label>

                    <Button type="submit" loading={loading}>
                      Search Jobs
                    </Button>
                  </div>
                </form>
              </Card>

              {/* Results */}
              <div className="jobs-results">
                {loading && jobs.length === 0 && (
                  <div className="loading">
                    <Loading />
                  </div>
                )}

                {jobs.length === 0 && !loading && (
                  <Card>
                    <div className="empty-state">
                      <p>No jobs found matching your criteria</p>
                      <p style={{fontSize: "14px", color: "#9ca3af", marginTop: "8px"}}>
                        Try adjusting your filters or search terms
                      </p>
                    </div>
                  </Card>
                )}

                <div className="jobs-grid">
                  {jobs.map(job => (
                    <JobCard
                      key={job.id}
                      job={job}
                      onSave={handleSaveJob}
                      onApply={handleApply}
                      onView={handleViewDetails}
                      saved={job.saved}
                    />
                  ))}
                </div>

                {hasMore && jobs.length > 0 && (
                  <div style={{textAlign: "center", paddingTop: "16px"}}>
                    <Button onClick={loadMoreJobs} loading={loading}>
                      Load More Jobs
                    </Button>
                  </div>
                )}

                {totalJobs > 0 && (
                  <p style={{textAlign: "center", fontSize: "14px", color: "#6b7280", marginTop: "16px"}}>
                    Showing {jobs.length} of {totalJobs} jobs
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Recommendations Tab */}
          {activeTab === "recommendations" && (
            <div>
              <div style={{display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px"}}>
                <h2 style={{fontSize: "18px", fontWeight: "600", margin: 0}}>Recommended for You</h2>
                <Button onClick={() => loadRecommendations()} loading={recLoading}>
                  Refresh
                </Button>
              </div>

              {recLoading && recommendations.length === 0 && (
                <div className="loading">
                  <Loading />
                </div>
              )}

              {recommendations.length === 0 && !recLoading && (
                <Card>
                  <div className="empty-state">
                    <p>No personalized recommendations yet</p>
                    <p style={{fontSize: "14px", color: "#9ca3af", marginTop: "8px", marginBottom: "16px"}}>
                      Complete your profile and upload a resume to get personalized matches
                    </p>
                    <Button onClick={() => navigate("/resume")}>
                      Complete Profile
                    </Button>
                  </div>
                </Card>
              )}

              <div className="jobs-grid">
                {recommendations.map(job => (
                  <JobCard
                    key={job.job_id || job.id}
                    job={job}
                    onSave={handleSaveJob}
                    onApply={() => {}}
                    onView={handleViewDetails}
                    saved={false}
                  />
                ))}
              </div>

              {recHasMore && recommendations.length > 0 && (
                <div style={{textAlign: "center", paddingTop: "16px"}}>
                  <Button onClick={loadMoreRecommendations} loading={recLoading}>
                    Load More
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Saved Tab */}
          {activeTab === "saved" && (
            <div>
              <div style={{display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px"}}>
                <h2 style={{fontSize: "18px", fontWeight: "600", margin: 0}}>Saved Jobs</h2>
                <span style={{fontSize: "14px", color: "#6b7280"}}>{savedJobs.length} saved</span>
              </div>

              {savedJobs.length === 0 ? (
                <Card>
                  <div className="empty-state">
                    <p>No saved jobs yet</p>
                    <p style={{fontSize: "14px", color: "#9ca3af", marginTop: "8px", marginBottom: "16px"}}>
                      Save jobs from search or recommendations to see them here
                    </p>
                    <Button onClick={() => setActiveTab("search")}>
                      Search Jobs
                    </Button>
                  </div>
                </Card>
              ) : (
                <div className="jobs-grid">
                  {savedJobs.map(job => (
                    <JobCard
                      key={job.id}
                      job={job}
                      onSave={handleUnsaveJob}
                      onApply={handleApply}
                      onView={handleViewDetails}
                      saved={true}
                      unsaveLabel="Remove"
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}

function JobCard({ job, onSave, onApply, onView, saved = false, unsaveLabel = "Unsave" }) {
  const salaryText = job.salary_min && job.salary_max
    ? `$${(job.salary_min / 1000).toFixed(0)}k - $${(job.salary_max / 1000).toFixed(0)}k`
    : job.salary_min
      ? `$${(job.salary_min / 1000).toFixed(0)}k+`
      : "Not specified";

  const tier = job.tier || "fair";

  return (
    <div className="job-card">
      <div className="job-card-header">
        <div className="job-card-info">
          <h3 className="job-card-title">{job.title}</h3>
          <p className="job-card-company">{job.company}</p>
        </div>
        {job.match_score !== undefined && (
          <div className="job-card-badges">
            <span className={`job-tier-badge tier-${tier}`}>{tier}</span>
            <span className="job-match-badge">{job.match_score}% Match</span>
          </div>
        )}
      </div>

      <div className="job-card-meta">
        <span>{job.location || "Remote"}</span>
        {job.experience_level && <span>{job.experience_level}</span>}
        <span>{salaryText}</span>
        {job.employment_type && <span>{job.employment_type}</span>}
      </div>

      {job.highlights && job.highlights.length > 0 && (
        <div className="job-card-tags">
          {job.highlights.slice(0, 3).map((highlight, i) => (
            <span key={i} className="job-tag">{highlight}</span>
          ))}
        </div>
      )}

      {job.matching_skills && job.matching_skills.length > 0 && (
        <div className="job-card-skills">
          <div className="job-skills-header">
            <span>Matching Skills</span>
            <span style={{color: "#2563eb"}}>{job.matching_skills.length} matched</span>
          </div>
          <div className="job-card-tags">
            {job.matching_skills.slice(0, 5).map((skill, i) => (
              <span key={i} className="job-tag tag-match">{skill.skill || skill}</span>
            ))}
          </div>
        </div>
      )}

      {job.missing_skills && job.missing_skills.length > 0 && (
        <div className="job-card-skills">
          <div className="job-skills-header">
            <span>Missing Skills</span>
            <span style={{color: "#dc2626"}}>{job.missing_skills.length} missing</span>
          </div>
          <div className="job-card-tags">
            {job.missing_skills.slice(0, 4).map((skill, i) => (
              <span key={i} className="job-tag tag-missing">{skill.skill || skill}</span>
            ))}
          </div>
        </div>
      )}

      <div className="job-card-actions">
        <Button onClick={() => onView(job.id || job.job_id)}>
          View Details
        </Button>
        <Button onClick={() => onSave(job.id || job.job_id)}>
          {saved ? unsaveLabel : "Save"}
        </Button>
        <Button onClick={() => onApply(job.id || job.job_id)}>
          Apply
        </Button>
      </div>
    </div>
  );
}

export default Jobs;
