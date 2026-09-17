import { useState, useEffect, useCallback } from "react";
import { careerService } from "../services";
import api from "../services/api";
import Card from "../components/common/Card";
import Loading from "../components/common/Loading";
import ErrorMessage from "../components/common/ErrorMessage";
import Button from "../components/common/Button";

function formatLabel(value) {
  if (value === null || value === undefined) return "";
  return String(value).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDate(value) {
  if (!value) return "";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString();
}

function Career() {
  const [activeTab, setActiveTab] = useState("paths");
  const [profile, setProfile] = useState(null);
  const [currentRole, setCurrentRole] = useState("Software Engineer");
  const [targetRole, setTargetRole] = useState("Senior Software Engineer");
  const [roleInput, setRoleInput] = useState("Software Engineer");
  const [targetInput, setTargetInput] = useState("Senior Software Engineer");

  useEffect(() => {
    const controller = new AbortController();
    async function loadProfile() {
      try {
        const response = await api.get("/api/profile/me");
        const data = response.data;
        if (data) {
          setProfile(data);
          const role = data.target_role || "Software Engineer";
          const headline = data.headline || "";
          setCurrentRole(headline || role);
          setRoleInput(headline || role);
          setTargetInput(role !== headline ? role : "Senior Software Engineer");
          setTargetRole(role !== headline ? role : "Senior Software Engineer");
        }
      } catch (err) {
        if (err.name === "CanceledError" || err.name === "AbortError") return;
      }
    }
    loadProfile();
    return () => controller.abort();
  }, []);

  const tabs = [
    { id: "assessment", label: "Assessment", icon: "🔍", desc: "Score, strengths & next actions" },
    { id: "paths", label: "Career Paths", icon: "📈", desc: "Roles, timelines & salary growth" },
    { id: "skills", label: "Skill Gaps", icon: "🎯", desc: "Missing & priority skills" },
    { id: "learning", label: "Learning Roadmap", icon: "📚", desc: "Phased learning plan" },
    { id: "strategy", label: "Job Strategy", icon: "💼", desc: "Search & positioning plan" },
    { id: "goals", label: "Goals", icon: "🏆", desc: "Track career milestones" },
  ];

  const handleApplyRoles = (e) => {
    e.preventDefault();
    setCurrentRole(roleInput);
    setTargetRole(targetInput);
  };

  return (
    <div className="page career-page">
      {/* Header */}
      <div className="career-head">
        <div className="career-head-text">
          <h1>Career Intelligence</h1>
          <p>Analyze your profile, discover career paths, and build a learning roadmap.</p>
        </div>
        <div className="career-ai-pill" title="Career guidance is generated from your profile and goals">
          <span className="career-ai-dot" aria-hidden="true" />
          <span className="career-ai-text">
            <strong>AI career guidance</strong>
            <small>Paths · gaps · plans</small>
          </span>
        </div>
      </div>

      {/* Role Selector */}
      <Card className="career-roles-card">
        <form onSubmit={handleApplyRoles} className="career-roles-form">
          <label className="career-field">
            <span className="career-field-label">Current Role</span>
            <input
              type="text"
              value={roleInput}
              onChange={(e) => setRoleInput(e.target.value)}
              placeholder="e.g. Software Engineer"
            />
          </label>
          <label className="career-field">
            <span className="career-field-label">Target Role</span>
            <input
              type="text"
              value={targetInput}
              onChange={(e) => setTargetInput(e.target.value)}
              placeholder="e.g. Senior Software Engineer"
            />
          </label>
          <Button type="submit">
            Update Analysis
          </Button>
        </form>
      </Card>

      {/* Dashboard navigation */}
      <nav className="career-nav" aria-label="Career sections">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            aria-pressed={activeTab === tab.id}
            className={`career-navcard ${activeTab === tab.id ? "active" : ""}`}
          >
            <span className="career-navicon" aria-hidden="true">{tab.icon}</span>
            <span className="career-navtext">
              <strong>{tab.label}</strong>
              <small>{tab.desc}</small>
            </span>
          </button>
        ))}
      </nav>

      {/* Tab Content */}
      {activeTab === "assessment" && <CareerAssessmentTab profile={profile} targetRole={targetRole} />}
      {activeTab === "paths" && <CareerPathsTab currentRole={currentRole} />}
      {activeTab === "skills" && <SkillGapsTab targetRole={targetRole} />}
      {activeTab === "learning" && <LearningRoadmapTab targetRole={targetRole} />}
      {activeTab === "strategy" && <JobStrategyTab targetRole={targetRole} />}
      {activeTab === "goals" && <GoalsTab />}
    </div>
  );
}

/* ============================================
   Career Assessment Tab
   ============================================ */

function CareerAssessmentTab({ profile, targetRole }) {
  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({
    current_role: "",
    years_experience: 0,
    skills: "",
    interests: "",
    weekly_learning_hours: 5,
    learning_budget: 0,
    learning_style: "mixed",
  });

  useEffect(() => {
    if (profile) {
      setForm(prev => ({
        ...prev,
        current_role: profile.headline || profile.target_role || "",
        years_experience: profile.years_of_experience || 0,
      }));
    }
  }, [profile]);

  const handleAssess = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = {
        current_role: form.current_role,
        years_experience: form.years_experience,
        skills: form.skills.split(",").map(s => s.trim()).filter(Boolean).map(s => ({ name: s })),
        target_role: targetRole,
        interests: form.interests.split(",").map(s => s.trim()).filter(Boolean),
        weekly_learning_hours: form.weekly_learning_hours,
        learning_budget: form.learning_budget,
        learning_style: form.learning_style,
      };
      const result = await careerService.assessCareer(data);
      setAssessment(result);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to complete assessment");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="career-stack">
      {error && <ErrorMessage message={error} />}

      <Card title="Career Assessment">
        <p className="career-card-sub">
          Get a comprehensive analysis of your career position, strengths, and areas for improvement.
        </p>
        <form onSubmit={handleAssess} className="career-form">
          <div className="career-field-grid cols-2">
            <label className="career-field">
              <span className="career-field-label">Current Role *</span>
              <input
                type="text"
                required
                value={form.current_role}
                onChange={(e) => setForm({ ...form, current_role: e.target.value })}
                placeholder="e.g. Software Engineer"
              />
            </label>
            <label className="career-field">
              <span className="career-field-label">Years of Experience *</span>
              <input
                type="number"
                required
                min="0"
                max="50"
                value={form.years_experience}
                onChange={(e) => setForm({ ...form, years_experience: parseInt(e.target.value) || 0 })}
              />
            </label>
          </div>
          <label className="career-field">
            <span className="career-field-label">Your Skills (comma separated)</span>
            <input
              type="text"
              value={form.skills}
              onChange={(e) => setForm({ ...form, skills: e.target.value })}
              placeholder="e.g. JavaScript, Python, React, Node.js"
            />
          </label>
          <label className="career-field">
            <span className="career-field-label">Interests (comma separated)</span>
            <input
              type="text"
              value={form.interests}
              onChange={(e) => setForm({ ...form, interests: e.target.value })}
              placeholder="e.g. Machine Learning, Cloud Architecture, Leadership"
            />
          </label>
          <div className="career-field-grid cols-3">
            <label className="career-field">
              <span className="career-field-label">Weekly Learning Hours</span>
              <input
                type="number"
                min="1"
                max="40"
                value={form.weekly_learning_hours}
                onChange={(e) => setForm({ ...form, weekly_learning_hours: parseInt(e.target.value) || 5 })}
              />
            </label>
            <label className="career-field">
              <span className="career-field-label">Learning Budget ($)</span>
              <input
                type="number"
                min="0"
                value={form.learning_budget}
                onChange={(e) => setForm({ ...form, learning_budget: parseFloat(e.target.value) || 0 })}
              />
            </label>
            <label className="career-field">
              <span className="career-field-label">Learning Style</span>
              <select
                value={form.learning_style}
                onChange={(e) => setForm({ ...form, learning_style: e.target.value })}
              >
                <option value="mixed">Mixed</option>
                <option value="visual">Visual</option>
                <option value="hands_on">Hands-on</option>
                <option value="reading">Reading</option>
              </select>
            </label>
          </div>
          <Button type="submit" loading={loading}>{loading ? "Assessing…" : "Run Assessment"}</Button>
        </form>
      </Card>

      {/* Assessment Results */}
      {assessment && (
        <div className="career-stack">
          <Card title="Assessment Results">
            <div className="career-score-hero">
              <div className="career-score-ring">
                <span className="career-score-value">{assessment.overall_score}</span>
                <span className="career-score-max">/ 100</span>
              </div>
              <div className="career-score-text">
                <h3>Overall Career Score</h3>
                <p>Readiness for your target role based on experience, skills, and trajectory.</p>
              </div>
            </div>

            {assessment.advice?.length > 0 && (
              <div className="career-advice-list">
                {assessment.advice.map((item, i) => (
                  <div key={i} className="career-advice-item">
                    <span className="career-advice-icon" aria-hidden="true">💡</span>
                    <div>
                      <p className="career-advice-title">{item.category || item.title || `Advice ${i + 1}`}</p>
                      <p className="career-advice-body">{item.advice || item.description || item.content}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <div className="career-two-col">
            {assessment.strengths?.length > 0 && (
              <Card title="Strengths">
                <ul className="career-tick-list">
                  {assessment.strengths.map((s, i) => (
                    <li key={i} className="good">
                      <span aria-hidden="true">✓</span>
                      {s}
                    </li>
                  ))}
                </ul>
              </Card>
            )}
            {assessment.areas_for_improvement?.length > 0 && (
              <Card title="Areas for Improvement">
                <ul className="career-tick-list">
                  {assessment.areas_for_improvement.map((a, i) => (
                    <li key={i} className="warn">
                      <span aria-hidden="true">⚠</span>
                      {a}
                    </li>
                  ))}
                </ul>
              </Card>
            )}
          </div>

          {assessment.next_actions?.length > 0 && (
            <Card title="Recommended Next Actions">
              <ol className="career-steps">
                {assessment.next_actions.map((action, i) => (
                  <li key={i}>
                    <span className="career-step-num" aria-hidden="true">{i + 1}</span>
                    <span>{action}</span>
                  </li>
                ))}
              </ol>
            </Card>
          )}

          {assessment.skill_gap_analysis && Object.keys(assessment.skill_gap_analysis).length > 0 && (
            <Card title="Skill Gap Analysis">
              <SkillGapAnalysisView analysis={assessment.skill_gap_analysis} />
            </Card>
          )}
        </div>
      )}

      {!assessment && !loading && (
        <Card>
          <div className="career-empty slim">
            <h3>Ready when you are</h3>
            <p>Fill in your details above and run an assessment to get personalized career insights.</p>
          </div>
        </Card>
      )}
    </div>
  );
}

/* ============================================
   Skill Gap Analysis View (maps real SkillGapAnalysis.to_dict() shape)
   ============================================ */

function SkillGapAnalysisView({ analysis }) {
  const targetRole = analysis.target_role || "—";
  const candidateSkills = analysis.candidate_skills || [];
  const requiredSkills = analysis.required_skills || [];
  const gaps = analysis.gaps || [];
  const matched = analysis.matched_skills || [];
  const score = typeof analysis.overall_match_score === "number" ? analysis.overall_match_score : 0;
  const critical = analysis.critical_gaps_count ?? gaps.filter((g) => (g.gap_severity ?? 0) >= 0.7).length;
  const moderate = analysis.moderate_gaps_count ?? gaps.filter((g) => (g.gap_severity ?? 0) >= 0.4 && (g.gap_severity ?? 0) < 0.7).length;
  const minor = analysis.minor_gaps_count ?? gaps.filter((g) => (g.gap_severity ?? 0) < 0.4).length;
  const totalWeeks = analysis.estimated_total_learning_time_weeks ?? gaps.reduce((s, g) => s + (g.estimated_learning_time_weeks || 0), 0);
  const priority = analysis.priority_skills || [];
  const timestamp = analysis.analysis_timestamp ? new Date(analysis.analysis_timestamp).toLocaleString() : null;

  return (
    <div className="career-stack">
      <div className="career-gap-head">
        <div>
          <p className="career-eyebrow">Target Role</p>
          <p className="career-gap-role">{targetRole}</p>
          {timestamp && <p className="career-muted">Analyzed: {timestamp}</p>}
        </div>
        <div className="career-gap-score">
          <p className="career-gap-pct">{Math.round(score * 100)}%</p>
          <p className="career-muted">Overall Match ({score.toFixed(2)} / 1.0)</p>
        </div>
      </div>

      <div className="career-stat-grid cols-4">
        <div className="career-stat good">
          <p className="career-stat-value">{matched.length}</p>
          <p className="career-stat-label">Matched Skills</p>
        </div>
        <div className="career-stat bad">
          <p className="career-stat-value">{critical}</p>
          <p className="career-stat-label">Critical Gaps</p>
        </div>
        <div className="career-stat warn">
          <p className="career-stat-value">{moderate}</p>
          <p className="career-stat-label">Moderate Gaps</p>
        </div>
        <div className="career-stat">
          <p className="career-stat-value">{minor}</p>
          <p className="career-stat-label">Minor Gaps</p>
        </div>
      </div>

      <div className="career-inline-meta">
        <span>👤 Candidate skills: <strong>{candidateSkills.length}</strong></span>
        <span>📋 Required skills: <strong>{requiredSkills.length}</strong></span>
        <span>⏱ Est. learning time: <strong>{totalWeeks} weeks</strong></span>
      </div>

      {priority.length > 0 && (
        <div>
          <p className="career-section-label">Priority Skills to Learn</p>
          <div className="career-chips">
            {priority.map((s, i) => (
              <span key={i} className="career-chip chip-blue">{s}</span>
            ))}
          </div>
        </div>
      )}

      {gaps.length > 0 && (
        <div>
          <p className="career-section-label">Gaps ({gaps.length})</p>
          <div className="career-gap-list">
            {gaps.map((g, i) => (
              <div key={i} className="career-gap-row">
                <span className="career-gap-name" title={g.skill_name}>{g.skill_name}</span>
                <div className="career-bar-track">
                  <div className="career-bar-fill bar-red" style={{ width: `${Math.min((g.gap_severity || 0) * 100, 100)}%` }} />
                </div>
                <span className="career-gap-levels" title={g.skill_name}>
                  {g.candidate_proficiency || "missing"} → {g.required_proficiency || "—"}
                  {g.estimated_learning_time_weeks ? ` · ${g.estimated_learning_time_weeks}w` : ""}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {matched.length > 0 && (
        <div>
          <p className="career-section-label">Matched Skills ({matched.length})</p>
          <div className="career-chips">
            {matched.map((m, i) => (
              <span key={i} className="career-chip chip-green" title={`${m.candidate_proficiency || ""} → ${m.required_proficiency || ""} (${Math.round((m.match_quality || 0) * 100)}%)`}>
                {m.skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {candidateSkills.length > 0 && (
        <div>
          <p className="career-section-label">Your Skills ({candidateSkills.length})</p>
          <div className="career-chips">
            {candidateSkills.map((s, i) => (
              <span key={i} className="career-chip">
                {s.name}{s.proficiency ? ` (${s.proficiency})` : ""}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ============================================
   Career Paths Tab
   ============================================ */

function CareerPathsTab({ currentRole }) {
  const [paths, setPaths] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    async function fetch() {
      try {
        setLoading(true);
        setError(null);
        const data = await careerService.getPathOptions(currentRole, controller.signal);
        setPaths(data);
      } catch (err) {
        if (err.name === "CanceledError" || err.name === "AbortError") return;
        setError(err.response?.data?.detail || err.message || "Failed to load career paths");
      } finally {
        setLoading(false);
      }
    }
    fetch();
    return () => controller.abort();
  }, [currentRole]);

  if (loading) return <Card><Loading /></Card>;
  if (error) return <Card><ErrorMessage message={error} /></Card>;
  if (!paths) return <Card><div className="career-empty slim"><p>No path data available.</p></div></Card>;

  const recommended = paths.recommended_path;
  const alternatives = paths.alternative_paths || [];

  return (
    <div className="career-stack">
      {recommended && (
        <Card title="Recommended Career Path">
          <div className="career-path-hero">
            <div>
              <p className="career-eyebrow">Destination Role</p>
              <h3>{recommended.target_role}</h3>
            </div>
            <div className="career-path-stats">
              <span className="career-path-stat">⏱ {recommended.total_estimated_time_months} months</span>
              <span className="career-path-stat good">📈 +{recommended.total_salary_growth_pct}% salary growth</span>
            </div>
          </div>
          <ol className="career-timeline">
            {(recommended.transitions || []).map((t, i) => (
              <li key={i} className="career-timeline-step">
                <span className="career-step-num" aria-hidden="true">{i + 1}</span>
                <div className="career-timeline-body">
                  <div className="career-timeline-head">
                    <div>
                      <h4>{t.to_role}</h4>
                      <p className="career-muted">{formatLabel(t.transition_type)} · {t.estimated_time_months} months</p>
                    </div>
                    <span className={`career-salary-chip ${t.salary_change_pct > 0 ? "up" : "down"}`}>
                      {t.salary_change_pct > 0 ? "+" : ""}{t.salary_change_pct}%
                    </span>
                  </div>
                  {t.required_additional_skills?.length > 0 && (
                    <div className="career-timeline-skills">
                      <p className="career-section-label small">Required Skills</p>
                      <div className="career-chips">
                        {t.required_additional_skills.slice(0, 6).map((s, j) => (
                          <span key={j} className="career-chip chip-blue">{s}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </Card>
      )}

      {alternatives.length > 0 && (
        <Card title="Alternative Paths">
          <div className="career-alt-grid">
            {alternatives.map((p, i) => (
              <div key={i} className="career-alt-card">
                <p className="career-alt-pivot">{formatLabel(p.transition_type) || "Career pivot"}</p>
                <h4>{p.target_role}</h4>
                <div className="career-alt-meta">
                  <span>⏱ {p.total_estimated_time_months} months</span>
                  <span className="good">📈 +{p.total_salary_growth_pct}%</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {paths.decision_factors && Object.keys(paths.decision_factors).length > 0 && (
        <Card title="Decision Factors">
          <div className="career-bars">
            {Object.entries(paths.decision_factors).map(([factor, score]) => (
              <div key={factor} className="career-bar-row">
                <span className="career-bar-label">{formatLabel(factor)}</span>
                <div className="career-bar-track">
                  <div className="career-bar-fill" style={{ width: `${Math.min((score || 0) * 100, 100)}%` }} />
                </div>
                <span className="career-bar-value">{Math.round((score || 0) * 100)}%</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {!recommended && alternatives.length === 0 && (
        <Card>
          <div className="career-empty slim">
            <h3>No paths found</h3>
            <p>No career paths found for "{currentRole}". Try updating your current role above.</p>
          </div>
        </Card>
      )}
    </div>
  );
}

/* ============================================
   Skill Gaps Tab
   ============================================ */

function SkillGapsTab({ targetRole }) {
  const [skills, setSkills] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSkill, setSelectedSkill] = useState(null);
  const [resources, setResources] = useState(null);
  const [resourcesLoading, setResourcesLoading] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    async function fetch() {
      try {
        setLoading(true);
        setError(null);
        const data = await careerService.getSkillRecommendations(targetRole, controller.signal);
        setSkills(data);
      } catch (err) {
        if (err.name === "CanceledError" || err.name === "AbortError") return;
        setError(err.response?.data?.detail || err.message || "Failed to load skill recommendations");
      } finally {
        setLoading(false);
      }
    }
    fetch();
    return () => controller.abort();
  }, [targetRole]);

  const fetchResources = async (skill) => {
    setSelectedSkill(skill);
    setResources(null);
    setResourcesLoading(true);
    try {
      const data = await careerService.getLearningResources(skill);
      setResources(data);
    } catch (err) {
      console.error("Failed to load resources:", err);
    } finally {
      setResourcesLoading(false);
    }
  };

  if (loading) return <Card><Loading /></Card>;
  if (error) return <Card><ErrorMessage message={error} /></Card>;
  if (!skills) return <Card><div className="career-empty slim"><p>No skill data available.</p></div></Card>;

  const gaps = skills.proficiency_gaps || [];
  const priority = skills.priority_skills || [];
  const missing = skills.missing_skills || [];
  const learningResources = skills.learning_resources || {};

  return (
    <div className="career-stack">
      <div className="career-stat-grid cols-3">
        <Card><div className="career-stat bad"><p className="career-stat-value">{missing.length}</p><p className="career-stat-label">Missing Skills</p></div></Card>
        <Card><div className="career-stat warn"><p className="career-stat-value">{gaps.length}</p><p className="career-stat-label">Proficiency Gaps</p></div></Card>
        <Card><div className="career-stat info"><p className="career-stat-value">{priority.length}</p><p className="career-stat-label">Priority Skills</p></div></Card>
      </div>

      {priority.length > 0 && (
        <Card title="Priority Skills to Learn">
          <p className="career-card-sub">Select a skill to find learning resources.</p>
          <div className="career-chips">
            {priority.map((skill, i) => (
              <button key={i} onClick={() => fetchResources(skill)} className={`career-chip-btn ${selectedSkill === skill ? "selected" : ""}`}>
                {skill}
              </button>
            ))}
          </div>
        </Card>
      )}

      {missing.length > 0 && (
        <Card title="Missing Skills">
          <div className="career-chips">
            {missing.map((skill, i) => (
              <button key={i} onClick={() => fetchResources(skill)} className="career-chip-btn missing">
                {skill}
              </button>
            ))}
          </div>
        </Card>
      )}

      {gaps.length > 0 && (
        <Card title="Proficiency Gaps">
          <div className="career-gap-list">
            {gaps.map((g, i) => (
              <div key={i} className="career-gap-row">
                <span className="career-gap-name" title={g.skill}>{g.skill}</span>
                <div className="career-bar-track">
                  <div className="career-bar-fill bar-amber" style={{ width: `${Math.min((g.gap_severity || 0) * 100, 100)}%` }} />
                </div>
                <span className="career-gap-levels">
                  {g.current || "—"} → {g.required || "—"}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {selectedSkill && (
        <Card title={`Learning Resources: ${selectedSkill}`}>
          {resourcesLoading ? <Loading /> : resources?.resources?.length > 0 ? (
            <div className="career-resource-list">
              {resources.resources.map((r, i) => (
                <div key={i} className="career-resource">
                  <div className="career-resource-main">
                    <h4>{r.title}</h4>
                    <p>{r.provider || ""}</p>
                    {r.url && <a href={r.url} target="_blank" rel="noopener noreferrer">View Resource →</a>}
                  </div>
                  {r.cost !== undefined && <span className="career-resource-cost">{r.cost === 0 ? "Free" : `$${r.cost}`}</span>}
                </div>
              ))}
            </div>
          ) : <p className="career-muted">No resources found.</p>}
          <div className="career-actions-row">
            <button type="button" className="career-ghostbtn" onClick={() => setSelectedSkill(null)}>Close</button>
          </div>
        </Card>
      )}

      {!selectedSkill && Object.keys(learningResources).length > 0 && (
        <Card title="Resources by Skill">
          <div className="career-link-list">
            {Object.entries(learningResources).map(([skill, resList]) => (
              <button key={skill} onClick={() => fetchResources(skill)} className="career-linkbtn">
                {skill} <span>({resList.length} resources)</span>
              </button>
            ))}
          </div>
        </Card>
      )}

      {gaps.length === 0 && missing.length === 0 && priority.length === 0 && (
        <Card><div className="career-empty slim"><h3>All clear</h3><p>No skill gaps identified for "{targetRole}".</p></div></Card>
      )}
    </div>
  );
}

/* ============================================
   Learning Roadmap Tab
   ============================================ */

function LearningRoadmapTab({ targetRole }) {
  const [plan, setPlan] = useState(null);
  const [error, setError] = useState(null);
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ target_skills: "", skill_gaps: "", weekly_hours: 10, learning_style: "mixed", budget: 0 });

  const handleCreatePlan = async (e) => {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const data = {
        target_role: targetRole,
        target_skills: form.target_skills.split(",").map(s => s.trim()).filter(Boolean),
        skill_gaps: form.skill_gaps.split(",").map(s => s.trim()).filter(Boolean),
        weekly_hours: form.weekly_hours,
        learning_style: form.learning_style,
        budget: form.budget,
      };
      const result = await careerService.createLearningPlan(data);
      setPlan(result);
      setShowForm(false);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to create learning plan");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="career-stack">
      {error && <ErrorMessage message={error} />}
      <Card title="Create Learning Plan">
        <p className="career-card-sub">Generate a personalized learning roadmap for becoming a <strong>{targetRole}</strong>.</p>
        {!showForm ? <Button onClick={() => setShowForm(true)}>Generate Learning Plan</Button> : (
          <form onSubmit={handleCreatePlan} className="career-form">
            <label className="career-field">
              <span className="career-field-label">Target Skills (comma separated)</span>
              <input type="text" value={form.target_skills} onChange={(e) => setForm({ ...form, target_skills: e.target.value })} placeholder="e.g. System Design, Leadership" />
            </label>
            <label className="career-field">
              <span className="career-field-label">Known Skill Gaps (comma separated)</span>
              <input type="text" value={form.skill_gaps} onChange={(e) => setForm({ ...form, skill_gaps: e.target.value })} placeholder="e.g. Kubernetes, Technical Writing" />
            </label>
            <div className="career-field-grid cols-3">
              <label className="career-field">
                <span className="career-field-label">Weekly Hours</span>
                <input type="number" min="1" max="40" value={form.weekly_hours} onChange={(e) => setForm({ ...form, weekly_hours: parseInt(e.target.value) || 10 })} />
              </label>
              <label className="career-field">
                <span className="career-field-label">Learning Style</span>
                <select value={form.learning_style} onChange={(e) => setForm({ ...form, learning_style: e.target.value })}><option value="mixed">Mixed</option><option value="visual">Visual</option><option value="hands_on">Hands-on</option><option value="reading">Reading</option></select>
              </label>
              <label className="career-field">
                <span className="career-field-label">Budget ($)</span>
                <input type="number" min="0" value={form.budget} onChange={(e) => setForm({ ...form, budget: parseFloat(e.target.value) || 0 })} />
              </label>
            </div>
            <div className="career-actions-row">
              <Button type="submit" loading={creating}>{creating ? "Creating…" : "Create Plan"}</Button>
              <button type="button" className="career-ghostbtn" onClick={() => setShowForm(false)}>Cancel</button>
            </div>
          </form>
        )}
      </Card>

      {plan && (
        <Card title={`Learning Plan: ${plan.target_role}`}>
          <div className="career-stat-grid cols-4">
            <div className="career-stat info"><p className="career-stat-value">{plan.total_estimated_weeks}</p><p className="career-stat-label">Weeks</p></div>
            <div className="career-stat good"><p className="career-stat-value">{plan.weekly_time_commitment_hours}h</p><p className="career-stat-label">Per Week</p></div>
            <div className="career-stat purple"><p className="career-stat-value">{plan.phases?.length || 0}</p><p className="career-stat-label">Phases</p></div>
            <div className="career-stat warn"><p className="career-stat-value">{plan.skill_gaps?.length || 0}</p><p className="career-stat-label">Skills</p></div>
          </div>
          {(plan.phases || []).length > 0 && (
            <div>
              <p className="career-section-label">Learning Phases</p>
              <ol className="career-timeline">
                {plan.phases.map((phase, i) => (
                  <li key={i} className="career-timeline-step">
                    <span className="career-step-num" aria-hidden="true">{i + 1}</span>
                    <div className="career-timeline-body">
                      <h4>{phase.name || `Phase ${i + 1}`}</h4>
                      <p className="career-muted">{phase.duration_weeks || phase.estimated_weeks || "?"} weeks</p>
                      {phase.focus_areas?.length > 0 && (
                        <div className="career-chips">
                          {phase.focus_areas.map((s, j) => (
                            <span key={j} className="career-chip chip-purple">{s}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          )}
          {plan.skill_gaps?.length > 0 && (
            <div>
              <p className="career-section-label">Skills Covered</p>
              <div className="career-chips">
                {plan.skill_gaps.map((s, i) => (
                  <span key={i} className="career-chip">{s}</span>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {!plan && !showForm && <Card><div className="career-empty slim"><h3>No plan yet</h3><p>Create a learning plan to get a personalized roadmap.</p></div></Card>}
    </div>
  );
}

/* ============================================
   Job Strategy Tab
   ============================================ */

function JobStrategyTab({ targetRole }) {
  const [strategy, setStrategy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    async function fetch() {
      try { setLoading(true); setError(null); const data = await careerService.getJobSearchStrategy(targetRole, controller.signal); setStrategy(data); }
      catch (err) { if (err.name === "CanceledError" || err.name === "AbortError") return; setError(err.response?.data?.detail || err.message || "Failed to load strategy"); }
      finally { setLoading(false); }
    }
    fetch();
    return () => controller.abort();
  }, [targetRole]);

  if (loading) return <Card><Loading /></Card>;
  if (error) return <Card><ErrorMessage message={error} /></Card>;
  if (!strategy) return <Card><div className="career-empty slim"><p>No strategy data available.</p></div></Card>;

  return (
    <div className="career-stack">
      {strategy.target_roles?.length > 0 && (
        <Card title="Target Roles">
          <div className="career-chips">
            {strategy.target_roles.map((role, i) => <span key={i} className="career-chip chip-blue">{role}</span>)}
          </div>
        </Card>
      )}
      {strategy.key_skills_to_highlight?.length > 0 && (
        <Card title="Key Skills to Highlight">
          <div className="career-chips">
            {strategy.key_skills_to_highlight.map((s, i) => <span key={i} className="career-chip chip-green">{s}</span>)}
          </div>
        </Card>
      )}
      {strategy.skill_gaps_to_address?.length > 0 && (
        <Card title="Skill Gaps to Address">
          <div className="career-chips">
            {strategy.skill_gaps_to_address.map((s, i) => <span key={i} className="career-chip chip-red">{s}</span>)}
          </div>
        </Card>
      )}
      {strategy.networking_strategy?.length > 0 && (
        <Card title="Networking Strategy">
          <ul className="career-tick-list">
            {strategy.networking_strategy.map((item, i) => <li key={i} className="info"><span aria-hidden="true">•</span>{item}</li>)}
          </ul>
        </Card>
      )}
      {strategy.salary_expectations && Object.keys(strategy.salary_expectations).length > 0 && (
        <Card title="Salary Expectations">
          <div className="career-salary-grid">
            {Object.entries(strategy.salary_expectations).map(([key, val]) => (
              <div key={key} className="career-salary-cell">
                <p className="career-salary-value">{typeof val === "number" ? `$${(val / 1000).toFixed(0)}k` : val}</p>
                <p className="career-salary-key">{formatLabel(key)}</p>
              </div>
            ))}
          </div>
        </Card>
      )}
      {strategy.preparation_checklist?.length > 0 && (
        <Card title="Preparation Checklist">
          <ul className="career-tick-list">
            {strategy.preparation_checklist.map((item, i) => <li key={i} className="check"><span aria-hidden="true">☐</span>{item}</li>)}
          </ul>
        </Card>
      )}
      {strategy.application_timeline && (
        <Card title="Application Timeline">
          <p className="career-timeline-note">{formatLabel(strategy.application_timeline)}</p>
        </Card>
      )}
    </div>
  );
}

/* ============================================
   Goals Tab
   ============================================ */

function GoalsTab() {
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", target_date: "", target_role: "", target_skills: "" });

  const fetchGoals = useCallback(async (signal) => {
    try { setLoading(true); const data = await careerService.getGoals(signal); setGoals(data); }
    catch (err) { if (err.name === "CanceledError" || err.name === "AbortError") return; setError(err.response?.data?.detail || err.message || "Failed to load goals"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { const c = new AbortController(); fetchGoals(c.signal); return () => c.abort(); }, [fetchGoals]);

  const handleCreateGoal = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      await careerService.createGoal({ title: form.title, description: form.description, target_date: form.target_date, target_role: form.target_role || undefined, target_skills: form.target_skills ? form.target_skills.split(",").map(s => s.trim()).filter(Boolean) : undefined });
      setShowForm(false); setForm({ title: "", description: "", target_date: "", target_role: "", target_skills: "" }); fetchGoals();
    } catch (err) { setError(err.response?.data?.detail || err.message || "Failed to create goal"); }
    finally { setCreating(false); }
  };

  if (loading) return <Card><Loading /></Card>;

  return (
    <div className="career-stack">
      {error && <ErrorMessage message={error} />}
      <Card title="Career Goals">
        <div className="career-goals-head">
          <p className="career-muted">{goals.length} goal{goals.length !== 1 ? "s" : ""}</p>
          <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "+ New Goal"}</Button>
        </div>
        {showForm && (
          <form onSubmit={handleCreateGoal} className="career-form bordered-top">
            <div className="career-field-grid cols-2">
              <label className="career-field">
                <span className="career-field-label">Goal Title *</span>
                <input type="text" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="e.g. Get promoted to Senior Engineer" />
              </label>
              <label className="career-field">
                <span className="career-field-label">Target Date *</span>
                <input type="date" required value={form.target_date} onChange={(e) => setForm({ ...form, target_date: e.target.value })} />
              </label>
            </div>
            <label className="career-field">
              <span className="career-field-label">Description *</span>
              <textarea required rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Describe what you want to achieve..." />
            </label>
            <div className="career-field-grid cols-2">
              <label className="career-field">
                <span className="career-field-label">Target Role</span>
                <input type="text" value={form.target_role} onChange={(e) => setForm({ ...form, target_role: e.target.value })} placeholder="e.g. Staff Engineer" />
              </label>
              <label className="career-field">
                <span className="career-field-label">Target Skills (comma separated)</span>
                <input type="text" value={form.target_skills} onChange={(e) => setForm({ ...form, target_skills: e.target.value })} placeholder="e.g. System Design, Leadership" />
              </label>
            </div>
            <Button type="submit" loading={creating}>{creating ? "Creating…" : "Create Goal"}</Button>
          </form>
        )}
      </Card>

      {goals.length === 0 ? (
        <Card><div className="career-empty slim"><h3>No goals yet</h3><p>No career goals yet. Create one to start tracking.</p></div></Card>
      ) : (
        <div className="career-goal-list">
          {goals.map((goal) => (
            <Card key={goal.id} className="career-goal-card">
              <div className="career-goal-top">
                <div className="career-goal-main">
                  <h3>{goal.title}</h3>
                  <p>{goal.description}</p>
                  <div className="career-goal-meta">
                    {goal.target_date && <span>📅 {formatDate(goal.target_date)}</span>}
                    {goal.target_role && <span>🎯 {goal.target_role}</span>}
                    {goal.target_skills?.length > 0 && (
                      <span className="career-goal-skills">
                        {goal.target_skills.map((s, j) => <span key={j} className="career-chip chip-purple small">{s}</span>)}
                      </span>
                    )}
                    {goal.progress !== undefined && <span>📊 {Math.round(goal.progress)}%</span>}
                  </div>
                </div>
                <span className={`career-status-pill ${goal.is_active ? "active" : ""}`}>
                  {goal.is_active ? "Active" : "Done"}
                </span>
              </div>
              {goal.progress !== undefined && (
                <div className="career-progress">
                  <div className="career-bar-track">
                    <div className="career-bar-fill" style={{ width: `${Math.min(goal.progress, 100)}%` }} />
                  </div>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

export default Career;
