import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { jobService, jobSearchService } from "../services";
import Button from "../components/common/Button";
import Card from "../components/common/Card";
import ErrorMessage from "../components/common/ErrorMessage";
import Loading from "../components/common/Loading";

const DEFAULT_SEARCH = {
  query: "",
  location: "",
  remote: false,
  experience_level: "",
  employment_type: "",
  skills: "",
  salary_min: "",
  page: 1,
  limit: 20,
};

function formatLabel(value) {
  if (!value) return "";
  return String(value).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatPostedDate(value) {
  if (!value) return "";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString();
}

function Jobs() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("search");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Search state
  const [jobs, setJobs] = useState([]);
  const [searchParams, setSearchParams] = useState({ ...DEFAULT_SEARCH });
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
      const response = await jobSearchService.listJobs({
        query: params.query.trim() || undefined,
        location: params.location.trim() || undefined,
        remote: params.remote || undefined,
        experience_level: params.experience_level || undefined,
        employment_type: params.employment_type || undefined,
        skills: params.skills.trim() || undefined,
        salary_min: params.salary_min || undefined,
        limit: params.limit,
        offset: ((overridePage ?? (append ? params.page : 1)) - 1) * params.limit,
      }, signal);

      const result = response?.data ?? response;
      const newJobs = Array.isArray(result) ? result : (result.jobs || []);
      const total = result.jobs_found ?? result.total ?? newJobs.length;

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

      const result = response?.data ?? response;
      const newRecs = result.recommendations || result;

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
      setSavedJobs(response?.data ?? response);
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

  const activeFilterCount = [
    searchParams.query.trim(),
    searchParams.location.trim(),
    searchParams.experience_level,
    searchParams.employment_type,
    searchParams.skills.trim(),
    searchParams.salary_min,
    searchParams.remote,
  ].filter(Boolean).length;

  const handleClearFilters = () => {
    setSearchParams({ ...DEFAULT_SEARCH });
    searchParamsRef.current = { ...DEFAULT_SEARCH };
    setError("");
    loadJobs(false);
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
    { id: "search", label: "Search Jobs", icon: "⌕" },
    { id: "recommendations", label: "For You", icon: "✦" },
    { id: "saved", label: "Saved", icon: "♥" },
  ];

  return (
    <div className="page jobs-page">
      {/* Page header */}
      <div className="jobs-page-head">
        <div className="jobs-page-head-text">
          <h1>Job Opportunities</h1>
          <p>Discover roles matched to your skills, experience, and career goals.</p>
        </div>
        <div className="jobs-ai-pill" title="Job ranking is powered by your profile and skills">
          <span className="jobs-ai-dot" aria-hidden="true" />
          <span className="jobs-ai-text">
            <strong>AI-powered matching</strong>
            <small>Ranked for your profile</small>
          </span>
        </div>
      </div>

      {error && (
        <div className="jobs-error">
          <ErrorMessage message={error} />
          {activeTab === "search" && (
            <Button onClick={() => loadJobs(false)} loading={loading}>Retry Search</Button>
          )}
          {activeTab === "recommendations" && (
            <Button onClick={() => loadRecommendations(false)} loading={recLoading}>Retry</Button>
          )}
        </div>
      )}

      <Card className="jobs-main-card">
        {/* Tabs */}
        <div className="jobs-tabbar" role="tablist" aria-label="Job views">
          {tabs.map(tab => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`jobs-tabbtn ${activeTab === tab.id ? "active" : ""}`}
            >
              <span className="jobs-tabicon" aria-hidden="true">{tab.icon}</span>
              {tab.label}
              {tab.id === "saved" && savedJobs.length > 0 && (
                <span className="jobs-tabcount">{savedJobs.length}</span>
              )}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="jobs-tabpanel">
          {/* Search Tab */}
          {activeTab === "search" && (
            <div>
              <section className="jobs-filter-card" aria-label="Search and filter jobs">
                <div className="jobs-filter-head">
                  <div>
                    <h2>Search &amp; Filter</h2>
                    <p>Narrow results by keywords, location, experience, and more.</p>
                  </div>
                  {activeFilterCount > 0 && (
                    <button type="button" className="jobs-clear" onClick={handleClearFilters}>
                      Clear filters ({activeFilterCount})
                    </button>
                  )}
                </div>

                <form onSubmit={handleSearch}>
                  <div className="jobs-field-grid">
                    <label className="jobs-field">
                      <span className="jobs-field-label"><span aria-hidden="true">⌕</span> Keywords</span>
                      <input
                        value={searchParams.query}
                        onChange={e => handleFilterChange("query", e.target.value)}
                        placeholder="Job title, company, keyword…"
                      />
                    </label>
                    <label className="jobs-field">
                      <span className="jobs-field-label"><span aria-hidden="true">📍</span> Location</span>
                      <input
                        value={searchParams.location}
                        onChange={e => handleFilterChange("location", e.target.value)}
                        placeholder="City, state, or Remote"
                      />
                    </label>
                    <label className="jobs-field">
                      <span className="jobs-field-label"><span aria-hidden="true">📶</span> Experience</span>
                      <select
                        value={searchParams.experience_level}
                        onChange={e => handleFilterChange("experience_level", e.target.value)}
                      >
                        <option value="">All levels</option>
                        <option value="entry">Entry</option>
                        <option value="junior">Junior</option>
                        <option value="mid">Mid</option>
                        <option value="senior">Senior</option>
                        <option value="lead">Lead</option>
                        <option value="principal">Principal</option>
                      </select>
                    </label>
                    <label className="jobs-field">
                      <span className="jobs-field-label"><span aria-hidden="true">💼</span> Job Type</span>
                      <select
                        value={searchParams.employment_type}
                        onChange={e => handleFilterChange("employment_type", e.target.value)}
                      >
                        <option value="">All types</option>
                        <option value="full_time">Full time</option>
                        <option value="part_time">Part time</option>
                        <option value="contract">Contract</option>
                        <option value="internship">Internship</option>
                      </select>
                    </label>
                    <label className="jobs-field">
                      <span className="jobs-field-label"><span aria-hidden="true">🛠</span> Skills</span>
                      <input
                        value={searchParams.skills}
                        onChange={e => handleFilterChange("skills", e.target.value)}
                        placeholder="Python, SQL, React"
                      />
                    </label>
                    <label className="jobs-field">
                      <span className="jobs-field-label"><span aria-hidden="true">💰</span> Min Salary</span>
                      <input
                        type="number"
                        min="0"
                        value={searchParams.salary_min}
                        onChange={e => handleFilterChange("salary_min", e.target.value)}
                        placeholder="e.g. 80000"
                      />
                    </label>
                  </div>

                  <div className="jobs-filter-foot">
                    <button
                      type="button"
                      role="switch"
                      aria-checked={searchParams.remote}
                      className={`jobs-remote-toggle ${searchParams.remote ? "on" : ""}`}
                      onClick={() => handleFilterChange("remote", !searchParams.remote)}
                    >
                      <span className="jobs-remote-knob" aria-hidden="true" />
                      <span className="jobs-remote-label">Remote only</span>
                    </button>

                    <Button type="submit" loading={loading}>
                      {loading ? "Searching…" : "⌕ Search Jobs"}
                    </Button>
                  </div>
                </form>
              </section>

              {/* Results */}
              <div className="jobs-results-head">
                <h2>{totalJobs > 0 ? `${totalJobs} ${totalJobs === 1 ? "role" : "roles"} found` : "Results"}</h2>
                {jobs.length > 0 && (
                  <span className="jobs-results-count">Showing {jobs.length} of {totalJobs}</span>
                )}
              </div>

              {loading && jobs.length === 0 && <JobsSkeleton />}

              {jobs.length === 0 && !loading && (
                <div className="jobs-empty">
                  <div className="jobs-empty-icon" aria-hidden="true">⌕</div>
                  <h3>No jobs found</h3>
                  <p>We couldn&apos;t find roles matching your current filters.</p>
                  <ul>
                    <li>Broaden your keywords or remove specific skills</li>
                    <li>Clear the location or try “Remote” instead</li>
                    <li>Turn off “Remote only” or lower the minimum salary</li>
                  </ul>
                  {activeFilterCount > 0 && (
                    <Button onClick={handleClearFilters}>Clear All Filters</Button>
                  )}
                </div>
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

              {loading && jobs.length > 0 && (
                <div className="jobs-inline-loading"><Loading message="Loading more jobs…" /></div>
              )}

              {hasMore && jobs.length > 0 && (
                <div className="jobs-more">
                  <Button onClick={loadMoreJobs} loading={loading}>
                    Load More Jobs
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Recommendations Tab */}
          {activeTab === "recommendations" && (
            <div>
              <div className="jobs-section-head">
                <div>
                  <h2>Recommended for You</h2>
                  <p>Personalized picks based on your profile, skills, and resume.</p>
                </div>
                <Button onClick={() => loadRecommendations(false)} loading={recLoading}>
                  ↺ Refresh
                </Button>
              </div>

              {recLoading && recommendations.length === 0 && <JobsSkeleton />}

              {recommendations.length === 0 && !recLoading && (
                <div className="jobs-empty">
                  <div className="jobs-empty-icon" aria-hidden="true">✦</div>
                  <h3>No personalized recommendations yet</h3>
                  <p>Complete your profile and upload a resume to unlock AI-matched roles.</p>
                  <ul>
                    <li>Add your skills and target role to your profile</li>
                    <li>Upload a resume so we can match your experience</li>
                  </ul>
                  <Button onClick={() => navigate("/resume")}>
                    Complete Profile
                  </Button>
                </div>
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
                <div className="jobs-more">
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
              <div className="jobs-section-head">
                <div>
                  <h2>Saved Jobs</h2>
                  <p>Roles you bookmarked to review or apply to later.</p>
                </div>
                <span className="jobs-results-count">{savedJobs.length} saved</span>
              </div>

              {savedJobs.length === 0 ? (
                <div className="jobs-empty">
                  <div className="jobs-empty-icon" aria-hidden="true">♥</div>
                  <h3>No saved jobs yet</h3>
                  <p>Save interesting roles from search or recommendations to find them here.</p>
                  <Button onClick={() => setActiveTab("search")}>
                    Search Jobs
                  </Button>
                </div>
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

function JobsSkeleton() {
  return (
    <div className="jobs-grid" aria-hidden="true">
      {[0, 1, 2].map(i => (
        <div key={i} className="jobs-skeleton-card">
          <div className="jobs-skeleton-row">
            <div className="jobs-skeleton-avatar" />
            <div className="jobs-skeleton-lines">
              <div className="jobs-skeleton-line wide" />
              <div className="jobs-skeleton-line" />
            </div>
          </div>
          <div className="jobs-skeleton-line" />
          <div className="jobs-skeleton-line short" />
          <div className="jobs-skeleton-chips">
            <div className="jobs-skeleton-chip" />
            <div className="jobs-skeleton-chip" />
            <div className="jobs-skeleton-chip" />
          </div>
        </div>
      ))}
    </div>
  );
}

function JobCard({ job, onSave, onApply, onView, saved = false, unsaveLabel = "Unsave" }) {
  const salaryMin = job.salary_min ?? job.salary_yearly_min;
  const salaryMax = job.salary_max ?? job.salary_yearly_max;
  const salaryText = salaryMin && salaryMax
    ? `$${(salaryMin / 1000).toFixed(0)}k – $${(salaryMax / 1000).toFixed(0)}k`
    : salaryMin
      ? `$${(salaryMin / 1000).toFixed(0)}k+`
      : "Salary not listed";

  const companyName = job.company_name || job.company || "Company not listed";
  const tier = job.tier || "fair";
  const posted = formatPostedDate(job.posted_date);
  const skills = Array.isArray(job.skills) ? job.skills : [];
  const extraSkills = skills.length > 5 ? skills.length - 5 : 0;
  const typeBadge = job.employment_type ? formatLabel(job.employment_type) : null;

  return (
    <article className="jobs-card">
      <div className="jobs-card-top">
        <div className="jobs-avatar" aria-hidden="true">
          {companyName.charAt(0).toUpperCase()}
        </div>
        <div className="jobs-card-heading">
          <h3 className="jobs-card-title">{job.title}</h3>
          <p className="jobs-card-company">{companyName}</p>
        </div>
        {job.match_score !== undefined && (
          <span className="jobs-match" title={`Match tier: ${tier}`}>{job.match_score}%</span>
        )}
      </div>

      <ul className="jobs-meta">
        <li><span aria-hidden="true">📍</span> {job.location || "Remote"} {job.remote ? "· Remote" : ""}</li>
        {typeBadge && <li><span aria-hidden="true">💼</span> {typeBadge}</li>}
        {job.experience_level && <li><span aria-hidden="true">📶</span> {formatLabel(job.experience_level)}</li>}
        <li><span aria-hidden="true">💰</span> {salaryText}</li>
        {posted && <li><span aria-hidden="true">🕒</span> Posted {posted}</li>}
      </ul>

      {job.description && (
        <p className="jobs-desc">{job.description.slice(0, 160)}{job.description.length > 160 ? "…" : ""}</p>
      )}

      {(skills.length > 0 || typeBadge) && (
        <div className="jobs-chips">
          {typeBadge && <span className="jobs-chip jobs-chip-type">{typeBadge}</span>}
          {skills.slice(0, 5).map(skill => <span key={skill} className="jobs-chip">{skill}</span>)}
          {extraSkills > 0 && <span className="jobs-chip jobs-chip-more">+{extraSkills} more</span>}
        </div>
      )}

      {job.highlights && job.highlights.length > 0 && (
        <ul className="jobs-highlights">
          {job.highlights.slice(0, 2).map((highlight, i) => (
            <li key={i}>{highlight}</li>
          ))}
        </ul>
      )}

      {job.matching_skills && job.matching_skills.length > 0 && (
        <div className="jobs-matchblock">
          <div className="jobs-matchblock-head">
            <span>Matching skills</span>
            <span className="jobs-matchblock-count good">{job.matching_skills.length} matched</span>
          </div>
          <div className="jobs-chips">
            {job.matching_skills.slice(0, 5).map((skill, i) => (
              <span key={i} className="jobs-chip jobs-chip-match">{skill.skill || skill}</span>
            ))}
          </div>
        </div>
      )}

      {job.missing_skills && job.missing_skills.length > 0 && (
        <div className="jobs-matchblock">
          <div className="jobs-matchblock-head">
            <span>Skills to grow</span>
            <span className="jobs-matchblock-count gap">{job.missing_skills.length} to learn</span>
          </div>
          <div className="jobs-chips">
            {job.missing_skills.slice(0, 4).map((skill, i) => (
              <span key={i} className="jobs-chip jobs-chip-missing">{skill.skill || skill}</span>
            ))}
          </div>
        </div>
      )}

      <div className="jobs-card-actions">
        <Button onClick={() => onView(job.id || job.job_id)}>
          View Details
        </Button>
        <button
          type="button"
          onClick={() => onSave(job.id || job.job_id)}
          className={`jobs-savebtn ${saved ? "saved" : ""}`}
          aria-pressed={saved}
        >
          {saved ? `♥ ${unsaveLabel}` : "♡ Save Job"}
        </button>
        {(job.application_url || job.source_url) ? (
          <a
            className="btn btn-primary jobs-applylink"
            href={job.application_url || job.source_url}
            target="_blank"
            rel="noreferrer"
          >
            Apply ↗
          </a>
        ) : (
          <Button onClick={() => onApply(job.id || job.job_id)}>Apply</Button>
        )}
      </div>
    </article>
  );
}

export default Jobs;
