import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthContext } from "../context/AuthContext";
import { jobService, jobSearchService } from "../services";
import Button from "../components/common/Button";
import Card from "../components/common/Card";
import ErrorMessage from "../components/common/ErrorMessage";
import Loading from "../components/common/Loading";
import Input from "../components/common/Input";
import Select from "../components/common/Select";

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

  // Ref to avoid stale closures in callbacks
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

  // Load jobs on mount only (not on every keystroke)
  useEffect(() => {
    const controller = new AbortController();
    loadJobs(false, controller.signal);
    return () => controller.abort();
  }, [loadJobs]);

  // Load recommendations when switching to that tab
  useEffect(() => {
    if (activeTab === "recommendations") {
      const controller = new AbortController();
      loadRecommendations(false, controller.signal);
      return () => controller.abort();
    }
  }, [activeTab, loadRecommendations]);

  // Load saved jobs when switching to that tab
  useEffect(() => {
    if (activeTab === "saved") {
      const controller = new AbortController();
      loadSavedJobs(controller.signal);
      return () => controller.abort();
    }
  }, [activeTab, loadSavedJobs]);

  const tabs = [
    { id: "search", label: "Search Jobs", icon: "🔍" },
    { id: "recommendations", label: "For You", icon: "✨" },
    { id: "saved", label: "Saved", icon: "💾" },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Job Opportunities</h1>
          <p className="text-gray-600 mt-2">Discover and match with relevant job opportunities</p>
        </div>

        {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          {/* Tabs */}
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px" aria-label="Tabs">
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? "border-blue-500 text-blue-600 bg-blue-50"
                      : "border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  {tab.label}
                  {tab.id === "saved" && savedJobs.length > 0 && (
                    <span className="ml-2 px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
                      {savedJobs.length}
                    </span>
                  )}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {/* Search Tab */}
            {activeTab === "search" && (
              <div>
                {/* Search Form */}
                <Card className="mb-6 p-6">
                  <form onSubmit={handleSearch} className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Keywords</label>
                        <Input
                          value={searchParams.query}
                          onChange={e => handleFilterChange("query", e.target.value)}
                          placeholder="Job title, skills, company..."
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
                        <Input
                          value={searchParams.location}
                          onChange={e => handleFilterChange("location", e.target.value)}
                          placeholder="City, state, or 'Remote'"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Experience</label>
                        <Select
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
                        </Select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Min Salary</label>
                        <Input
                          type="number"
                          value={searchParams.salary_min}
                          onChange={e => handleFilterChange("salary_min", e.target.value)}
                          placeholder="$50,000"
                        />
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-4">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={searchParams.remote}
                          onChange={e => handleFilterChange("remote", e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="text-sm text-gray-700">Remote Only</span>
                      </label>
                      
                      <Button type="submit" loading={loading} className="ml-auto">
                        Search Jobs
                      </Button>
                    </div>
                  </form>
                </Card>

                {/* Results */}
                <div className="space-y-4">
                  {loading && jobs.length === 0 && (
                    <div className="text-center py-12">
                      <Loading />
                    </div>
                  )}

                  {jobs.length === 0 && !loading && (
                    <Card className="p-8 text-center">
                      <p className="text-gray-500 mb-4">No jobs found matching your criteria</p>
                      <p className="text-sm text-gray-400">Try adjusting your filters or search terms</p>
                    </Card>
                  )}

                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
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

                  {hasMore && (
                    <div className="text-center pt-4">
                      <Button onClick={loadMoreJobs} loading={loading} variant="secondary">
                        Load More Jobs
                      </Button>
                    </div>
                  )}

                  {totalJobs > 0 && (
                    <p className="text-center text-sm text-gray-500 mt-4">
                      Showing {jobs.length} of {totalJobs} jobs
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Recommendations Tab */}
            {activeTab === "recommendations" && (
              <div>
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-lg font-medium text-gray-900">Recommended for You</h2>
                  <Button onClick={loadRecommendations} loading={recLoading} variant="secondary">
                    Refresh
                  </Button>
                </div>

                {recLoading && recommendations.length === 0 && (
                  <div className="text-center py-12">
                    <Loading />
                  </div>
                )}

                {recommendations.length === 0 && !recLoading && (
                  <Card className="p-8 text-center">
                    <p className="text-gray-500 mb-4">No personalized recommendations yet</p>
                    <p className="text-sm text-gray-400 mb-4">Complete your profile and upload a resume to get personalized matches</p>
                    <Button onClick={() => navigate("/resume")} variant="primary">
                      Complete Profile
                    </Button>
                  </Card>
                )}

                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {recommendations.map(job => (
                    <JobRecommendationCard
                      key={job.job_id || job.id}
                      job={job}
                      onSave={handleSaveJob}
                      onView={handleViewDetails}
                    />
                  ))}
                </div>

                {recHasMore && (
                  <div className="text-center pt-4">
                    <Button onClick={loadMoreRecommendations} loading={recLoading} variant="secondary">
                      Load More
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* Saved Tab */}
            {activeTab === "saved" && (
              <div>
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-lg font-medium text-gray-900">Saved Jobs</h2>
                  <span className="text-sm text-gray-500">{savedJobs.length} saved</span>
                </div>

                {savedJobs.length === 0 ? (
                  <Card className="p-8 text-center">
                    <p className="text-gray-500 mb-4">No saved jobs yet</p>
                    <p className="text-sm text-gray-400 mb-4">Save jobs from search or recommendations to see them here</p>
                    <Button onClick={() => setActiveTab("search")} variant="primary">
                      Search Jobs
                    </Button>
                  </Card>
                ) : (
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
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
        </div>
      </div>
    </div>
  );
}

function JobCard({ job, onSave, onApply, onView, saved = false, unsaveLabel = "Unsave" }) {
  const salaryText = job.salary_min && job.salary_max 
    ? `$${(job.salary_min / 1000).toFixed(0)}k - $${(job.salary_max / 1000).toFixed(0)}k`
    : job.salary_min 
      ? `$${(job.salary_min / 1000).toFixed(0)}k+`
      : "Salary not specified";

  const matchScore = job.match_score || 0;
  const tier = job.tier || "fair";
  const tierColors = {
    excellent: "bg-emerald-100 text-emerald-800",
    good: "bg-green-100 text-green-800",
    fair: "bg-yellow-100 text-yellow-800",
    poor: "bg-red-100 text-red-800",
  };

  return (
    <Card className="p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-gray-900 truncate">{job.title}</h3>
          <p className="text-sm text-gray-500 mt-1">{job.company}</p>
        </div>
        {job.match_score !== undefined && (
          <div className="flex items-center gap-2 ml-3">
            <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${tierColors[tier] || tierColors.fair}`}>
              {tier}
            </span>
            <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
              {job.match_score}% Match
            </span>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-3 text-sm text-gray-600 mb-4">
        <span className="flex items-center gap-1">📍 {job.location || "Remote"}</span>
        {job.experience_level && <span className="flex items-center gap-1">📊 {job.experience_level}</span>}
        <span className="flex items-center gap-1">💰 {salaryText}</span>
        {job.employment_type && <span className="flex items-center gap-1">🏢 {job.employment_type}</span>}
      </div>

      {job.highlights && job.highlights.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-4">
          {job.highlights.slice(0, 3).map((highlight, i) => (
            <span key={i} className="px-2 py-0.5 text-xs bg-gray-100 text-gray-700 rounded">
              {highlight}
            </span>
          ))}
        </div>
      )}

      {job.matching_skills && job.matching_skills.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-gray-500">Matching Skills</span>
            <span className="text-green-600 font-medium">{job.matching_skills.length} matched</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {job.matching_skills.slice(0, 5).map((skill, i) => (
              <span key={i} className="px-2 py-0.5 text-xs bg-green-50 text-green-700 rounded border border-green-200">
                {skill.skill || skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {job.missing_skills && job.missing_skills.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-gray-500">Missing Skills</span>
            <span className="text-red-600 font-medium">{job.missing_skills.length} missing</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {job.missing_skills.slice(0, 4).map((skill, i) => (
              <span key={i} className="px-2 py-0.5 text-xs bg-red-50 text-red-700 rounded border border-red-200">
                {skill.skill || skill}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-2 pt-3 border-t border-gray-100">
        <Button 
          onClick={() => onView(job.id || job.job_id)}
          variant="secondary"
          className="flex-1"
        >
          View Details
        </Button>
        <Button
          onClick={e => { e.stopPropagation(); onSave(job.id || job.job_id); }}
          variant={saved ? "danger" : "secondary"}
          className="flex-1"
        >
          {saved ? unsaveLabel : "Save"}
        </Button>
        <Button
          onClick={e => { e.stopPropagation(); onApply(job.id || job.job_id); }}
          variant="primary"
          className="flex-1"
        >
          Apply
        </Button>
      </div>
    </Card>
  );
}

function JobRecommendationCard({ job, onSave, onView }) {
  const matchScore = job.match_score || 0;
  const tier = job.tier || "fair";
  const tierColors = {
    excellent: "bg-emerald-100 text-emerald-800",
    good: "bg-green-100 text-green-800",
    fair: "bg-yellow-100 text-yellow-800",
    poor: "bg-red-100 text-red-800",
  };

  return (
    <Card className="p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-gray-900 truncate">{job.title}</h3>
          <p className="text-sm text-gray-500 mt-1">{job.company}</p>
        </div>
        <div className="flex items-center gap-2 ml-3">
          <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${tierColors[tier] || tierColors.fair}`}>
            {tier}
          </span>
          <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
            {job.match_score}% Match
          </span>
        </div>
      </div>

      <div className="flex flex-wrap gap-3 text-sm text-gray-600 mb-4">
        <span className="flex items-center gap-1">📍 {job.location || "Remote"}</span>
        {job.salary_min && job.salary_max && (
          <span className="flex items-center gap-1">💰 ${(job.salary_min / 1000).toFixed(0)}k - ${(job.salary_max / 1000).toFixed(0)}k</span>
        )}
        {job.experience_level && <span className="flex items-center gap-1">📊 {job.experience_level}</span>}
      </div>

      {job.matching_skills && job.matching_skills.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-gray-500">Matching Skills</span>
            <span className="text-green-600 font-medium">{job.matching_skills.length} matched</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {job.matching_skills.slice(0, 4).map((skill, i) => (
              <span key={i} className="px-2 py-0.5 text-xs bg-green-50 text-green-700 rounded border border-green-200">
                {skill.skill || skill}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-2 pt-3 border-t border-gray-100">
        <Button onClick={() => onView(job.job_id || job.id)} variant="secondary" className="flex-1">
          View Details
        </Button>
        <Button onClick={e => { e.stopPropagation(); onSave(job.job_id || job.id); }} variant="secondary" className="flex-1">
          Save
        </Button>
      </div>
    </Card>
  );
}

export default Jobs;