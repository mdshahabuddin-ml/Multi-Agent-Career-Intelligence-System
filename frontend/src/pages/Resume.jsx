import { useState, useEffect, useCallback } from "react";
import { resumeService } from "../services";
import { atsService } from "../services";
import Button from "../components/common/Button";
import Card from "../components/common/Card";
import ErrorMessage from "../components/common/ErrorMessage";
import Loading from "../components/common/Loading";
import FileUpload from "../components/common/FileUpload";

const SUPPORTED_FORMATS_LABEL = "PDF, DOC, DOCX, TXT";
const MAX_SIZE_LABEL = "10 MB";

function formatFileSize(bytes) {
  if (bytes === null || bytes === undefined) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value) {
  if (!value) return "";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString();
}

function formatLabel(value) {
  if (!value) return "";
  return String(value).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function scoreTone(score) {
  if (typeof score !== "number") return "none";
  if (score >= 80) return "good";
  if (score >= 60) return "fair";
  return "low";
}

function Resume() {
  const [activeTab, setActiveTab] = useState("upload");
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [error, setError] = useState("");
  const [resumes, setResumes] = useState([]);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [selectedResume, setSelectedResume] = useState(null);
  const [resumeDetails, setResumeDetails] = useState(null);

  const handleFileUpload = async (file) => {
    if (!file) return;

    setError("");
    setUploading(true);

    try {
      // uploadResume already returns response.data ({ id, filename, status, message })
      const response = await resumeService.uploadResume(file);
      const uploaded = response.data ?? response;
      // Refresh for full record fields (size, dates, flags), then select it
      const list = await fetchResumes();
      const fresh = (uploaded && list.find(r => r.id === uploaded.id)) || list[0] || null;
      if (fresh) {
        setSelectedResume(fresh);
        setResumeDetails(null);
        setAnalysisResult(null);
        fetchDetails(fresh.id);
      }
      setActiveTab("analyze");
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  // Resolve the analyzable text for a resume using existing APIs:
  // details first, otherwise fetch; (re-)parse server-side when no text
  // is stored yet — including resumes marked failed, so one transient
  // failure can never permanently block analysis. Retries the parse once.
  const resolveResumeText = async (resumeId) => {
    let details = (resumeDetails && resumeDetails.id === resumeId) ? resumeDetails : null;
    if (!details) {
      try {
        const response = await resumeService.getResume(resumeId);
        details = response.data ?? response ?? null;
        if (details) setResumeDetails(details);
      } catch (err) {
        console.error("Failed to fetch resume details:", err);
      }
    }
    if (details && !details.raw_text) {
      setParsing(true);
      try {
        let lastError = null;
        for (let attempt = 0; attempt < 2; attempt++) {
          try {
            await resumeService.parseResume(resumeId);
            lastError = null;
            break;
          } catch (err) {
            lastError = err;
            console.error(`Resume parse attempt ${attempt + 1} failed:`, err);
          }
        }
        if (lastError) throw lastError;
        const refetched = await resumeService.getResume(resumeId);
        details = refetched.data ?? refetched ?? details;
        setResumeDetails(details);
      } catch (err) {
        console.error("Failed to parse resume:", err);
        throw err;
      } finally {
        setParsing(false);
      }
    }
    return details?.raw_text || "";
  };

  const NO_TEXT_MESSAGE = "Could not extract readable text from this resume. Try re-uploading a text-based PDF, DOCX, or TXT file.";

  const handleAnalyze = async (resumeId) => {
    setError("");
    setAnalyzing(true);

    try {
      const text = await resolveResumeText(resumeId);
      if (!text || !text.trim()) {
        setError(NO_TEXT_MESSAGE);
        return;
      }
      const result = await atsService.analyzeResume(text, { resume_id: resumeId });
      setAnalysisResult(result);
    } catch (err) {
      setError(err.response?.data?.detail || NO_TEXT_MESSAGE);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleOptimize = async (resumeId, jobDescription) => {
    setError("");
    setAnalyzing(true);

    try {
      const text = await resolveResumeText(resumeId);
      if (!text || !text.trim()) {
        setError(NO_TEXT_MESSAGE);
        return;
      }
      // atsService forwards `jobDescription` (camelCase) to the API
      const result = await atsService.analyzeResume(text, { resume_id: resumeId, jobDescription });
      setAnalysisResult(prev => ({ ...prev, optimization: result }));
    } catch (err) {
      setError(err.response?.data?.detail || "Optimization failed");
    } finally {
      setAnalyzing(false);
    }
  };

  const fetchResumes = useCallback(async () => {
    setLoadingList(true);
    try {
      const response = await resumeService.listResumes();
      // listResumes already returns response.data (an array)
      const list = response.data ?? response ?? [];
      const clean = Array.isArray(list) ? list.filter(Boolean) : [];
      setResumes(clean);
      return clean;
    } catch (err) {
      console.error("Failed to fetch resumes:", err);
      return [];
    } finally {
      setLoadingList(false);
    }
  }, []);

  const fetchDetails = useCallback(async (resumeId) => {
    if (!resumeId) return;
    setLoadingDetails(true);
    try {
      const response = await resumeService.getResume(resumeId);
      setResumeDetails(response.data ?? response ?? null);
    } catch (err) {
      console.error("Failed to fetch resume details:", err);
      setResumeDetails(null);
    } finally {
      setLoadingDetails(false);
    }
  }, []);

  const handleSelectResume = useCallback((resume, tab = "analyze") => {
    setSelectedResume(resume);
    setResumeDetails(null);
    setAnalysisResult(null);
    setError("");
    fetchDetails(resume.id);
    setActiveTab(tab);
  }, [fetchDetails]);

  const handleSetPrimary = async (resumeId) => {
    setError("");
    try {
      await resumeService.setPrimary(resumeId);
      setResumes(prev => prev.map(r => ({ ...r, is_primary: r.id === resumeId })));
      setSelectedResume(prev => (prev && prev.id === resumeId ? { ...prev, is_primary: true } : prev));
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to set primary resume");
    }
  };

  const handleDelete = async (resume) => {
    if (!window.confirm(`Delete "${resume.original_filename || resume.filename}"?`)) return;
    setError("");
    try {
      await resumeService.deleteResume(resume.id);
      setResumes(prev => prev.filter(r => r.id !== resume.id));
      if (selectedResume && selectedResume.id === resume.id) {
        setSelectedResume(null);
        setResumeDetails(null);
        setAnalysisResult(null);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Delete failed");
    }
  };

  useEffect(() => {
    fetchResumes();
  }, [fetchResumes]);

  // Auto-select the primary (or most recent) resume so the Analyze tab
  // is immediately usable instead of stuck on "No resume selected".
  useEffect(() => {
    if (!selectedResume && resumes.length > 0 && !loadingList) {
      const primary = resumes.find(r => r && r.is_primary) || resumes.find(Boolean);
      if (primary) {
        setSelectedResume(primary);
        fetchDetails(primary.id);
      }
    }
  }, [resumes, selectedResume, loadingList, fetchDetails]);

  useEffect(() => {
    if (activeTab === "analyze" && selectedResume && !resumeDetails && !loadingDetails) {
      fetchDetails(selectedResume.id);
    }
  }, [activeTab, selectedResume, resumeDetails, loadingDetails, fetchDetails]);

  const tabs = [
    { id: "upload", label: "Upload Resume", icon: "⬆" },
    { id: "analyze", label: "Analyze & Optimize", icon: "✦" },
    { id: "manage", label: "My Resumes", icon: "▤" },
  ];

  return (
    <div className="page resume-page">
      {/* Header */}
      <div className="resume-head">
        <div className="resume-head-text">
          <h1>Resume Intelligence</h1>
          <p>Upload, analyze, and optimize your resume with AI-powered ATS insights.</p>
        </div>
        <div className="resume-ai-pill" title="Resume scoring uses ATS compatibility and content analysis">
          <span className="resume-ai-dot" aria-hidden="true" />
          <span className="resume-ai-text">
            <strong>AI-powered analysis</strong>
            <small>ATS + content review</small>
          </span>
        </div>
      </div>

      {error && (
        <div className="resume-error">
          <ErrorMessage message={error} />
        </div>
      )}

      <Card className="resume-main-card">
        {/* Tabs */}
        <div className="resume-tabbar" role="tablist" aria-label="Resume workspace">
          {tabs.map(tab => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`resume-tabbtn ${activeTab === tab.id ? "active" : ""}`}
            >
              <span className="resume-tabicon" aria-hidden="true">{tab.icon}</span>
              {tab.label}
              {tab.id === "manage" && resumes.length > 0 && (
                <span className="resume-tabcount">{resumes.length}</span>
              )}
            </button>
          ))}
        </div>

        <div className="resume-tabpanel">
          {/* Upload Tab */}
          {activeTab === "upload" && (
            <div className="resume-upload-wrap">
              <FileUpload
                onUpload={handleFileUpload}
                loading={uploading}
                accept=".pdf,.doc,.docx,.txt"
                maxSize={10 * 1024 * 1024}
                title="Upload Your Resume"
                description={`Supported formats: ${SUPPORTED_FORMATS_LABEL} (max ${MAX_SIZE_LABEL})`}
                submitLabel={uploading ? "Uploading…" : "Upload Resume"}
              />

              <div className="resume-formats">
                {["PDF", "DOC", "DOCX", "TXT"].map(fmt => (
                  <span key={fmt} className="resume-format-chip">{fmt}</span>
                ))}
                <span className="resume-format-note">Max file size {MAX_SIZE_LABEL}</span>
              </div>

              <div className="resume-tips">
                <h3>Tips for best results</h3>
                <ul>
                  <li>Use a clean, single-column format</li>
                  <li>Include clear section headers (Experience, Education, Skills)</li>
                  <li>Quantify achievements with numbers and metrics</li>
                  <li>Include relevant keywords for your target role</li>
                </ul>
              </div>
            </div>
          )}

          {/* Analyze Tab */}
          {activeTab === "analyze" && (
            <div>
              {!selectedResume ? (
                <div className="resume-empty">
                  <div className="resume-empty-icon" aria-hidden="true">✦</div>
                  <h3>No resume selected</h3>
                  <p>Upload a resume or pick one from your library to run ATS analysis and optimization.</p>
                  <div className="resume-empty-actions">
                    <Button onClick={() => setActiveTab("upload")}>Upload Resume</Button>
                    <button
                      type="button"
                      className="resume-ghostbtn"
                      onClick={() => { fetchResumes(); setActiveTab("manage"); }}
                    >
                      Browse My Resumes
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <div className="resume-selected">
                    <div className="resume-selected-avatar" aria-hidden="true">
                      {(selectedResume.original_filename || selectedResume.filename || "R").charAt(0).toUpperCase()}
                    </div>
                    <div className="resume-selected-info">
                      <h3>{selectedResume.original_filename || selectedResume.filename}</h3>
                      <p>
                        {[selectedResume.file_size ? formatFileSize(selectedResume.file_size) : "",
                          formatDate(selectedResume.created_at),
                          selectedResume.status ? formatLabel(selectedResume.status) : ""].filter(Boolean).join("  ·  ")}
                      </p>
                    </div>
                    {resumes.length > 1 && (
                      <label className="resume-picker">
                        <span className="resume-picker-label">Resume</span>
                        <select
                          value={selectedResume.id}
                          onChange={e => {
                            const found = resumes.find(r => String(r.id) === e.target.value);
                            if (found) handleSelectResume(found, "analyze");
                          }}
                          aria-label="Select resume to analyze"
                        >
                          {resumes.map(r => (
                            <option key={r.id} value={r.id}>
                              {r.original_filename || r.filename}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                    {selectedResume.is_primary && <span className="resume-primary-badge">★ Primary</span>}
                    <span className="resume-ready-badge">Ready for analysis</span>
                  </div>

                  {loadingDetails || parsing ? (
                    <div className="resume-inline-loading">
                      <Loading message={parsing ? "Extracting resume text…" : "Loading resume details…"} />
                    </div>
                  ) : analysisResult ? (
                    <AnalysisResults
                      result={analysisResult}
                      details={resumeDetails || selectedResume}
                      resumeId={selectedResume.id}
                      onOptimize={handleOptimize}
                      analyzing={analyzing}
                    />
                  ) : (
                    <div className="resume-cta">
                      <h3>Ready to Analyze</h3>
                      <p>Get ATS compatibility scoring, keyword gaps, and targeted optimization suggestions for this resume.</p>
                      <Button
                        onClick={() => handleAnalyze(selectedResume.id)}
                        loading={analyzing || parsing}
                      >
                        {parsing ? "Extracting text…" : analyzing ? "Analyzing…" : "✦ Analyze Resume"}
                      </Button>
                    </div>
                  )}

                  {analyzing && analysisResult && (
                    <div className="resume-inline-loading"><Loading message="Updating analysis…" /></div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Manage Tab */}
          {activeTab === "manage" && (
            <div>
              <div className="resume-section-head">
                <div>
                  <h2>My Resumes</h2>
                  <p>{resumes.length > 0 ? `${resumes.length} ${resumes.length === 1 ? "resume" : "resumes"} in your library` : "Resumes you upload will appear here."}</p>
                </div>
                <Button onClick={() => setActiveTab("upload")}>+ Upload New</Button>
              </div>

              {loadingList ? (
                <div className="resume-inline-loading"><Loading message="Loading resumes…" /></div>
              ) : resumes.length === 0 ? (
                <div className="resume-empty">
                  <div className="resume-empty-icon" aria-hidden="true">▤</div>
                  <h3>No resumes yet</h3>
                  <p>Upload your first resume to unlock ATS scoring and AI optimization.</p>
                  <Button onClick={() => setActiveTab("upload")}>Upload Your First Resume</Button>
                </div>
              ) : (
                <div className="resume-grid">
                  {resumes.map(resume => (
                    <ResumeCard
                      key={resume.id}
                      resume={resume}
                      selected={selectedResume && selectedResume.id === resume.id}
                      onView={() => handleSelectResume(resume, "analyze")}
                      onAnalyze={() => { handleSelectResume(resume, "analyze"); handleAnalyze(resume.id); }}
                      onSetPrimary={() => handleSetPrimary(resume.id)}
                      onDelete={() => handleDelete(resume)}
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

function ScoreRing({ score }) {
  const tone = scoreTone(score);
  return (
    <div className={`resume-score-ring tone-${tone}`}>
      <span className="resume-score-value">{typeof score === "number" ? Math.round(score) : "—"}</span>
      <span className="resume-score-max">/ 100</span>
    </div>
  );
}

function AnalysisResults({ result, details, resumeId, onOptimize, analyzing }) {
  // Real API shape is flat: { overall_score, passed, issues, keyword_match_score,
  // format_score, section_score, content_score, missing_keywords, matched_keywords,
  // recommendations }. Older responses may nest under `ats_analysis` — support both,
  // but never invent values.
  const ats = result?.ats_analysis ?? result ?? {};
  const hasScore = typeof ats.overall_score === "number";
  const verdict = !hasScore ? "Not scored yet"
    : ats.overall_score >= 80 ? "Excellent" : ats.overall_score >= 60 ? "Good" : "Needs Improvement";

  const breakdown = [
    { label: "Keyword match", value: ats.keyword_match_score },
    { label: "Format", value: ats.format_score },
    { label: "Sections", value: ats.section_score },
    { label: "Content", value: ats.content_score },
  ].filter(b => typeof b.value === "number");

  const skills = Array.isArray(details?.extracted_skills) ? details.extracted_skills : [];
  const experience = Array.isArray(details?.extracted_experience) ? details.extracted_experience : [];
  const education = Array.isArray(details?.extracted_education) ? details.extracted_education : [];
  const missing = Array.isArray(ats.missing_keywords) ? ats.missing_keywords : [];
  const matched = Array.isArray(ats.matched_keywords) ? ats.matched_keywords : [];
  const recommendations = Array.isArray(ats.recommendations) ? ats.recommendations : [];
  const issues = Array.isArray(ats.issues) ? ats.issues : [];

  return (
    <div className="resume-analysis">
      {/* ATS Score hero */}
      <div className="resume-score-hero">
        <div className="resume-score-hero-text">
          <p className="resume-eyebrow">ATS Compatibility</p>
          <h3>{hasScore ? verdict : "Analysis complete"}</h3>
          <p>
            {hasScore
              ? "How well this resume passes Applicant Tracking Systems."
              : "The analyzer did not return a score for this resume."}
          </p>
          {typeof ats.passed === "boolean" && (
            <span className={`resume-passed ${ats.passed ? "pass" : "fail"}`}>
              {ats.passed ? "✓ ATS check passed" : "✕ ATS check needs work"}
            </span>
          )}
        </div>
        <ScoreRing score={hasScore ? ats.overall_score : null} />
      </div>

      {/* Score breakdown */}
      {breakdown.length > 0 && (
        <div className="resume-panel">
          <h3>Score Breakdown</h3>
          <div className="resume-bars">
            {breakdown.map(b => (
              <div key={b.label} className="resume-bar-row">
                <span className="resume-bar-label">{b.label}</span>
                <div className="resume-bar-track">
                  <div className="resume-bar-fill" style={{ width: `${Math.min(Math.max(b.value, 0), 100)}%` }} />
                </div>
                <span className="resume-bar-value">{Math.round(b.value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="resume-panels">
        {/* Skills */}
        {skills.length > 0 && (
          <div className="resume-panel">
            <h3>Skills <span className="resume-count">{skills.length}</span></h3>
            <div className="resume-chips">
              {skills.slice(0, 20).map((s, i) => (
                <span key={i} className="resume-chip">{typeof s === "string" ? s : s.name || JSON.stringify(s)}</span>
              ))}
            </div>
          </div>
        )}

        {/* Experience */}
        {experience.length > 0 && (
          <div className="resume-panel">
            <h3>Experience <span className="resume-count">{experience.length}</span></h3>
            <ul className="resume-list">
              {experience.slice(0, 5).map((e, i) => (
                <li key={i}>
                  <strong>{e.role || e.title || e.position || "Role not specified"}</strong>
                  <span>{[e.company || e.organization, e.duration || e.dates || e.years].filter(Boolean).join(" · ")}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Education */}
        {education.length > 0 && (
          <div className="resume-panel">
            <h3>Education <span className="resume-count">{education.length}</span></h3>
            <ul className="resume-list">
              {education.slice(0, 5).map((e, i) => (
                <li key={i}>
                  <strong>{typeof e === "string" ? e : (e.degree || e.school || e.institution || "Education entry")}</strong>
                  {typeof e === "object" && e !== null && (
                    <span>{[e.school || e.institution, e.year || e.dates].filter(Boolean).join(" · ")}</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Missing Keywords */}
        {missing.length > 0 && (
          <div className="resume-panel">
            <h3>Missing Keywords <span className="resume-count">{missing.length}</span></h3>
            <p className="resume-panel-sub">Add these to improve ATS matching.</p>
            <div className="resume-chips">
              {missing.slice(0, 15).map((keyword, i) => (
                <span key={i} className="resume-chip chip-missing">{typeof keyword === "string" ? keyword : keyword.keyword || JSON.stringify(keyword)}</span>
              ))}
            </div>
          </div>
        )}

        {/* Matched Keywords */}
        {matched.length > 0 && (
          <div className="resume-panel">
            <h3>Matched Keywords <span className="resume-count">{matched.length}</span></h3>
            <p className="resume-panel-sub">Already present in your resume.</p>
            <div className="resume-chips">
              {matched.slice(0, 15).map((keyword, i) => (
                <span key={i} className="resume-chip chip-matched">{typeof keyword === "string" ? keyword : keyword.keyword || JSON.stringify(keyword)}</span>
              ))}
            </div>
          </div>
        )}

        {/* Issues */}
        {issues.length > 0 && (
          <div className="resume-panel">
            <h3>Detected Issues <span className="resume-count">{issues.length}</span></h3>
            <ul className="resume-issues">
              {issues.map((issue, i) => (
                <li key={i}>
                  <span className={`resume-sev sev-${String(issue.severity || "info").toLowerCase()}`} aria-hidden="true" />
                  <div>
                    <strong>{issue.title || formatLabel(issue.type) || `Issue ${i + 1}`}</strong>
                    {issue.description && <p>{issue.description}</p>}
                    {issue.suggestion && <p className="resume-suggestion">→ {issue.suggestion}</p>}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recommendations */}
        {recommendations.length > 0 && (
          <div className="resume-panel">
            <h3>Improvement Suggestions</h3>
            <ul className="resume-recs">
              {recommendations.map((rec, i) => (
                <li key={i}>
                  <span className="resume-check" aria-hidden="true">✓</span>
                  {typeof rec === "string" ? rec : rec.text || JSON.stringify(rec)}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Optimization */}
      {result?.optimization && (
        <div className="resume-panel">
          <h3>Optimized Version</h3>
          <div className="resume-code">
            {result.optimization.optimized_resume || JSON.stringify(result.optimization, null, 2)}
          </div>
          {result.optimization.optimized_resume && (
            <div className="resume-panel-actions">
              <button
                type="button"
                className="resume-ghostbtn"
                onClick={() => navigator.clipboard.writeText(result.optimization.optimized_resume)}
              >
                Copy to Clipboard
              </button>
            </div>
          )}
        </div>
      )}

      {/* Job Description Optimization */}
      <div className="resume-panel">
        <h3>Optimize for a Specific Job</h3>
        <p className="resume-panel-sub">Paste a job description to get targeted suggestions.</p>
        <JobOptimizationForm resumeId={resumeId} onOptimize={onOptimize} analyzing={analyzing} />
      </div>
    </div>
  );
}

function JobOptimizationForm({ resumeId, onOptimize, analyzing }) {
  const [jobDescription, setJobDescription] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (jobDescription.trim()) {
      onOptimize(resumeId, jobDescription);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="resume-optform">
      <textarea
        value={jobDescription}
        onChange={e => setJobDescription(e.target.value)}
        placeholder="Paste job description here…"
        rows={5}
        required
      />
      <Button type="submit" loading={analyzing}>
        {analyzing ? "Optimizing…" : "Optimize for This Job"}
      </Button>
    </form>
  );
}

function ResumeCard({ resume, selected, onView, onAnalyze, onSetPrimary, onDelete }) {
  const tone = scoreTone(resume.ats_score);
  return (
    <article className={`resume-card ${selected ? "selected" : ""}`}>
      <div className="resume-card-top">
        <div className="resume-card-avatar" aria-hidden="true">
          {(resume.original_filename || resume.filename || "R").charAt(0).toUpperCase()}
        </div>
        <div className="resume-card-heading">
          <h3 title={resume.original_filename || resume.filename}>{resume.original_filename || resume.filename}</h3>
          <p>
            {[resume.file_size ? formatFileSize(resume.file_size) : "",
              formatDate(resume.created_at),
              resume.status ? formatLabel(resume.status) : ""].filter(Boolean).join("  ·  ")}
          </p>
        </div>
        <button
          type="button"
          onClick={onDelete}
          className="resume-iconbtn danger"
          aria-label={`Delete ${resume.original_filename || resume.filename}`}
          title="Delete resume"
        >
          🗑
        </button>
      </div>

      <div className="resume-card-meta">
        {resume.is_primary && <span className="resume-primary-badge">★ Primary</span>}
        {typeof resume.ats_score === "number" ? (
          <span className={`resume-score-chip tone-${tone}`}>ATS {Math.round(resume.ats_score)}/100</span>
        ) : (
          <span className="resume-score-chip tone-none">Not scored yet</span>
        )}
      </div>

      <div className="resume-card-actions">
        <button type="button" className="resume-ghostbtn" onClick={onView}>View</button>
        <button type="button" className="resume-ghostbtn" onClick={() => onAnalyze()}>✦ Analyze</button>
        {!resume.is_primary && (
          <button type="button" className="resume-ghostbtn" onClick={onSetPrimary} title="Set as primary resume">
            ☆ Primary
          </button>
        )}
      </div>
    </article>
  );
}

export default Resume;
