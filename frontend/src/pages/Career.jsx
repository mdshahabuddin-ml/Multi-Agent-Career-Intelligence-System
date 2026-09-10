import { useState, useEffect, useCallback, useContext } from "react";
import { careerService } from "../services";
import api from "../services/api";
import Card from "../components/common/Card";
import Loading from "../components/common/Loading";
import ErrorMessage from "../components/common/ErrorMessage";
import Button from "../components/common/Button";

function Career() {
  const [activeTab, setActiveTab] = useState("paths");
  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(true);
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
      } finally {
        setProfileLoading(false);
      }
    }
    loadProfile();
    return () => controller.abort();
  }, []);

  const tabs = [
    { id: "assessment", label: "Assessment", icon: "🔍" },
    { id: "paths", label: "Career Paths", icon: "📈" },
    { id: "skills", label: "Skill Gaps", icon: "🎯" },
    { id: "learning", label: "Learning Roadmap", icon: "📚" },
    { id: "strategy", label: "Job Strategy", icon: "💼" },
    { id: "goals", label: "Goals", icon: "🏆" },
  ];

  const handleApplyRoles = (e) => {
    e.preventDefault();
    setCurrentRole(roleInput);
    setTargetRole(targetInput);
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1>Career Intelligence</h1>
        <p>Analyze your profile, discover career paths, and build a learning roadmap</p>
      </div>

      {/* Role Selector */}
      <Card className="mb-6">
        <form onSubmit={handleApplyRoles} className="flex flex-col sm:flex-row items-end gap-4">
          <div className="flex-1 w-full">
            <label className="block text-sm font-medium text-gray-700 mb-1">Current Role</label>
            <input
              type="text"
              value={roleInput}
              onChange={(e) => setRoleInput(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="e.g. Software Engineer"
            />
          </div>
          <div className="flex-1 w-full">
            <label className="block text-sm font-medium text-gray-700 mb-1">Target Role</label>
            <input
              type="text"
              value={targetInput}
              onChange={(e) => setTargetInput(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="e.g. Senior Software Engineer"
            />
          </div>
          <Button type="submit" className="whitespace-nowrap">
            Update Analysis
          </Button>
        </form>
      </Card>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-1 -mb-px overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              <span className="mr-1">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

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
    <div className="space-y-6">
      {error && <ErrorMessage message={error} />}

      <Card title="Career Assessment">
        <p className="text-sm text-gray-600 mb-4">
          Get a comprehensive analysis of your career position, strengths, and areas for improvement.
        </p>
        <form onSubmit={handleAssess} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Current Role *</label>
              <input
                type="text"
                required
                value={form.current_role}
                onChange={(e) => setForm({ ...form, current_role: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="e.g. Software Engineer"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Years of Experience *</label>
              <input
                type="number"
                required
                min="0"
                max="50"
                value={form.years_experience}
                onChange={(e) => setForm({ ...form, years_experience: parseInt(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Your Skills (comma separated)</label>
            <input
              type="text"
              value={form.skills}
              onChange={(e) => setForm({ ...form, skills: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="e.g. JavaScript, Python, React, Node.js"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Interests (comma separated)</label>
            <input
              type="text"
              value={form.interests}
              onChange={(e) => setForm({ ...form, interests: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="e.g. Machine Learning, Cloud Architecture, Leadership"
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Weekly Learning Hours</label>
              <input
                type="number"
                min="1"
                max="40"
                value={form.weekly_learning_hours}
                onChange={(e) => setForm({ ...form, weekly_learning_hours: parseInt(e.target.value) || 5 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Learning Budget ($)</label>
              <input
                type="number"
                min="0"
                value={form.learning_budget}
                onChange={(e) => setForm({ ...form, learning_budget: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Learning Style</label>
              <select
                value={form.learning_style}
                onChange={(e) => setForm({ ...form, learning_style: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="mixed">Mixed</option>
                <option value="visual">Visual</option>
                <option value="hands_on">Hands-on</option>
                <option value="reading">Reading</option>
              </select>
            </div>
          </div>
          <Button type="submit" loading={loading}>Run Assessment</Button>
        </form>
      </Card>

      {/* Assessment Results */}
      {assessment && (
        <div className="space-y-6">
          {/* Overall Score */}
          <Card title="Assessment Results">
            <div className="text-center mb-6">
              <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-blue-100 mb-3">
                <span className="text-3xl font-bold text-blue-700">{assessment.overall_score}</span>
              </div>
              <p className="text-sm text-gray-500">Overall Career Score (out of 10)</p>
            </div>

            {/* Advice */}
            {assessment.advice?.length > 0 && (
              <div className="space-y-2">
                {assessment.advice.map((item, i) => (
                  <div key={i} className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg">
                    <span className="text-blue-600 mt-0.5">💡</span>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{item.category || item.title || `Advice ${i + 1}`}</p>
                      <p className="text-sm text-gray-600 mt-0.5">{item.advice || item.description || item.content}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Strengths & Improvements */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {assessment.strengths?.length > 0 && (
              <Card title="Strengths">
                <ul className="space-y-2">
                  {assessment.strengths.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="text-green-500 mt-0.5">✓</span>
                      {s}
                    </li>
                  ))}
                </ul>
              </Card>
            )}
            {assessment.areas_for_improvement?.length > 0 && (
              <Card title="Areas for Improvement">
                <ul className="space-y-2">
                  {assessment.areas_for_improvement.map((a, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="text-yellow-500 mt-0.5">⚠</span>
                      {a}
                    </li>
                  ))}
                </ul>
              </Card>
            )}
          </div>

          {/* Next Actions */}
          {assessment.next_actions?.length > 0 && (
            <Card title="Recommended Next Actions">
              <div className="space-y-2">
                {assessment.next_actions.map((action, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                    <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-sm font-bold">
                      {i + 1}
                    </span>
                    <span className="text-sm text-gray-700">{action}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Skill Gap Analysis */}
          {assessment.skill_gap_analysis && Object.keys(assessment.skill_gap_analysis).length > 0 && (
            <Card title="Skill Gap Analysis">
              <div className="space-y-3">
                {Object.entries(assessment.skill_gap_analysis).map(([skill, data]) => (
                  <div key={skill} className="flex items-center gap-3">
                    <span className="text-sm text-gray-700 w-36">{skill}</span>
                    <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 rounded-full"
                        style={{ width: `${Math.min((data.current || 0) / (data.required || 1) * 100, 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500 w-20 text-right">
                      {data.current || 0}/{data.required || 10}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {!assessment && !loading && (
        <Card>
          <p className="text-gray-500 text-center py-8">
            Fill in your details above and run an assessment to get personalized career insights.
          </p>
        </Card>
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
  if (!paths) return <Card><p className="text-gray-500">No path data available.</p></Card>;

  const recommended = paths.recommended_path;
  const alternatives = paths.alternative_paths || [];

  return (
    <div className="space-y-6">
      {recommended && (
        <Card title="Recommended Career Path">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-gray-900">{recommended.target_role}</h3>
            <div className="flex flex-wrap gap-4 mt-2 text-sm text-gray-600">
              <span>⏱ {recommended.total_estimated_time_months} months</span>
              <span>📈 +{recommended.total_salary_growth_pct}% salary growth</span>
            </div>
          </div>
          <div className="space-y-4">
            {(recommended.transitions || []).map((t, i) => (
              <div key={i} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="w-7 h-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-sm font-bold">{i + 1}</span>
                      <h4 className="font-medium text-gray-900">{t.to_role}</h4>
                    </div>
                    <p className="text-sm text-gray-500 mt-1 ml-9">{t.transition_type} · {t.estimated_time_months} months</p>
                  </div>
                  <span className={`text-sm font-medium ${t.salary_change_pct > 0 ? "text-green-600" : "text-red-600"}`}>
                    {t.salary_change_pct > 0 ? "+" : ""}{t.salary_change_pct}%
                  </span>
                </div>
                {t.required_additional_skills?.length > 0 && (
                  <div className="mt-3 ml-9">
                    <p className="text-xs text-gray-500 mb-1">Required Skills:</p>
                    <div className="flex flex-wrap gap-1">
                      {t.required_additional_skills.slice(0, 6).map((s, j) => (
                        <span key={j} className="px-2 py-0.5 text-xs bg-blue-50 text-blue-700 rounded border border-blue-200">{s}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {alternatives.length > 0 && (
        <Card title="Alternative Paths">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {alternatives.map((p, i) => (
              <div key={i} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                <h4 className="font-medium text-gray-900">{p.target_role}</h4>
                <div className="flex flex-wrap gap-3 mt-2 text-sm text-gray-600">
                  <span>⏱ {p.total_estimated_time_months} months</span>
                  <span>📈 +{p.total_salary_growth_pct}%</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {paths.decision_factors && Object.keys(paths.decision_factors).length > 0 && (
        <Card title="Decision Factors">
          <div className="space-y-3">
            {Object.entries(paths.decision_factors).map(([factor, score]) => (
              <div key={factor} className="flex items-center gap-3">
                <span className="text-sm text-gray-700 w-40 capitalize">{factor.replace(/_/g, " ")}</span>
                <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-full" style={{ width: `${Math.min((score || 0) * 100, 100)}%` }} />
                </div>
                <span className="text-sm text-gray-500 w-12 text-right">{Math.round((score || 0) * 100)}%</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {!recommended && alternatives.length === 0 && (
        <Card>
          <p className="text-gray-500 text-center py-8">No career paths found for "{currentRole}". Try updating your current role above.</p>
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
  if (!skills) return <Card><p className="text-gray-500">No skill data available.</p></Card>;

  const gaps = skills.proficiency_gaps || [];
  const priority = skills.priority_skills || [];
  const missing = skills.missing_skills || [];
  const learningResources = skills.learning_resources || {};

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <Card><div className="text-center"><p className="text-3xl font-bold text-red-600">{missing.length}</p><p className="text-sm text-gray-500 mt-1">Missing Skills</p></div></Card>
        <Card><div className="text-center"><p className="text-3xl font-bold text-yellow-600">{gaps.length}</p><p className="text-sm text-gray-500 mt-1">Proficiency Gaps</p></div></Card>
        <Card><div className="text-center"><p className="text-3xl font-bold text-blue-600">{priority.length}</p><p className="text-sm text-gray-500 mt-1">Priority Skills</p></div></Card>
      </div>

      {priority.length > 0 && (
        <Card title="Priority Skills to Learn">
          <div className="flex flex-wrap gap-2">
            {priority.map((skill, i) => (
              <button key={i} onClick={() => fetchResources(skill)} className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${selectedSkill === skill ? "bg-blue-100 text-blue-700 border-blue-300" : "bg-gray-50 text-gray-700 border-gray-200 hover:bg-blue-50 hover:text-blue-600"}`}>
                {skill}
              </button>
            ))}
          </div>
        </Card>
      )}

      {missing.length > 0 && (
        <Card title="Missing Skills">
          <div className="flex flex-wrap gap-2">
            {missing.map((skill, i) => (
              <button key={i} onClick={() => fetchResources(skill)} className="px-3 py-1.5 text-sm rounded-full bg-red-50 text-red-700 border border-red-200 hover:bg-red-100 transition-colors">
                {skill}
              </button>
            ))}
          </div>
        </Card>
      )}

      {selectedSkill && (
        <Card title={`Learning Resources: ${selectedSkill}`}>
          {resourcesLoading ? <Loading /> : resources?.resources?.length > 0 ? (
            <div className="space-y-3">
              {resources.resources.map((r, i) => (
                <div key={i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900">{r.title}</h4>
                    <p className="text-sm text-gray-600 mt-0.5">{r.provider || ""}</p>
                    {r.url && <a href={r.url} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline mt-1 inline-block">View Resource →</a>}
                  </div>
                  {r.cost !== undefined && <span className="text-sm text-gray-500">{r.cost === 0 ? "Free" : `$${r.cost}`}</span>}
                </div>
              ))}
            </div>
          ) : <p className="text-gray-500">No resources found.</p>}
          <Button variant="secondary" className="mt-4" onClick={() => setSelectedSkill(null)}>Close</Button>
        </Card>
      )}

      {!selectedSkill && Object.keys(learningResources).length > 0 && (
        <Card title="Resources by Skill">
          <div className="space-y-2">
            {Object.entries(learningResources).map(([skill, resList]) => (
              <button key={skill} onClick={() => fetchResources(skill)} className="text-sm font-medium text-blue-600 hover:underline">
                {skill} ({resList.length} resources)
              </button>
            ))}
          </div>
        </Card>
      )}

      {gaps.length === 0 && missing.length === 0 && priority.length === 0 && (
        <Card><p className="text-gray-500 text-center py-8">No skill gaps identified for "{targetRole}".</p></Card>
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
    <div className="space-y-6">
      {error && <ErrorMessage message={error} />}
      <Card title="Create Learning Plan">
        <p className="text-sm text-gray-600 mb-4">Generate a personalized learning roadmap for becoming a <strong>{targetRole}</strong>.</p>
        {!showForm ? <Button onClick={() => setShowForm(true)}>Generate Learning Plan</Button> : (
          <form onSubmit={handleCreatePlan} className="space-y-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Target Skills (comma separated)</label><input type="text" value={form.target_skills} onChange={(e) => setForm({ ...form, target_skills: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="e.g. System Design, Leadership" /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Known Skill Gaps (comma separated)</label><input type="text" value={form.skill_gaps} onChange={(e) => setForm({ ...form, skill_gaps: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="e.g. Kubernetes, Technical Writing" /></div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Weekly Hours</label><input type="number" min="1" max="40" value={form.weekly_hours} onChange={(e) => setForm({ ...form, weekly_hours: parseInt(e.target.value) || 10 })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" /></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Learning Style</label><select value={form.learning_style} onChange={(e) => setForm({ ...form, learning_style: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"><option value="mixed">Mixed</option><option value="visual">Visual</option><option value="hands_on">Hands-on</option><option value="reading">Reading</option></select></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Budget ($)</label><input type="number" min="0" value={form.budget} onChange={(e) => setForm({ ...form, budget: parseFloat(e.target.value) || 0 })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" /></div>
            </div>
            <div className="flex gap-3"><Button type="submit" loading={creating}>Create Plan</Button><Button type="button" variant="secondary" onClick={() => setShowForm(false)}>Cancel</Button></div>
          </form>
        )}
      </Card>

      {plan && (
        <Card title={`Learning Plan: ${plan.target_role}`}>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
            <div className="text-center"><p className="text-2xl font-bold text-blue-600">{plan.total_estimated_weeks}</p><p className="text-xs text-gray-500">Weeks</p></div>
            <div className="text-center"><p className="text-2xl font-bold text-green-600">{plan.weekly_time_commitment_hours}h</p><p className="text-xs text-gray-500">Per Week</p></div>
            <div className="text-center"><p className="text-2xl font-bold text-purple-600">{plan.phases?.length || 0}</p><p className="text-xs text-gray-500">Phases</p></div>
            <div className="text-center"><p className="text-2xl font-bold text-orange-600">{plan.skill_gaps?.length || 0}</p><p className="text-xs text-gray-500">Skills</p></div>
          </div>
          {(plan.phases || []).length > 0 && (
            <div className="space-y-4">
              <h4 className="font-medium text-gray-900">Learning Phases</h4>
              {plan.phases.map((phase, i) => (
                <div key={i} className="border border-gray-200 rounded-lg p-4">
                  <h5 className="font-medium text-gray-900">Phase {i + 1}: {phase.name || `Phase ${i + 1}`}</h5>
                  <p className="text-sm text-gray-500 mt-0.5">{phase.duration_weeks || phase.estimated_weeks || "?"} weeks</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {!plan && !showForm && <Card><p className="text-gray-500 text-center py-8">Create a learning plan to get a personalized roadmap.</p></Card>}
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
  if (!strategy) return <Card><p className="text-gray-500">No strategy data available.</p></Card>;

  return (
    <div className="space-y-6">
      {strategy.target_roles?.length > 0 && <Card title="Target Roles"><div className="flex flex-wrap gap-2">{strategy.target_roles.map((role, i) => <span key={i} className="px-3 py-1 text-sm bg-blue-50 text-blue-700 rounded-full border border-blue-200">{role}</span>)}</div></Card>}
      {strategy.key_skills_to_highlight?.length > 0 && <Card title="Key Skills to Highlight"><div className="flex flex-wrap gap-2">{strategy.key_skills_to_highlight.map((s, i) => <span key={i} className="px-3 py-1 text-sm bg-green-50 text-green-700 rounded-full border border-green-200">{s}</span>)}</div></Card>}
      {strategy.skill_gaps_to_address?.length > 0 && <Card title="Skill Gaps to Address"><div className="flex flex-wrap gap-2">{strategy.skill_gaps_to_address.map((s, i) => <span key={i} className="px-3 py-1 text-sm bg-red-50 text-red-700 rounded-full border border-red-200">{s}</span>)}</div></Card>}
      {strategy.networking_strategy?.length > 0 && <Card title="Networking Strategy"><ul className="space-y-2">{strategy.networking_strategy.map((item, i) => <li key={i} className="flex items-start gap-2 text-sm text-gray-700"><span className="text-blue-500 mt-0.5">•</span>{item}</li>)}</ul></Card>}
      {strategy.salary_expectations && Object.keys(strategy.salary_expectations).length > 0 && <Card title="Salary Expectations"><div className="grid grid-cols-2 sm:grid-cols-4 gap-4">{Object.entries(strategy.salary_expectations).map(([key, val]) => <div key={key} className="text-center"><p className="text-lg font-bold text-gray-900">{typeof val === "number" ? `$${(val / 1000).toFixed(0)}k` : val}</p><p className="text-xs text-gray-500 capitalize">{key.replace(/_/g, " ")}</p></div>)}</div></Card>}
      {strategy.preparation_checklist?.length > 0 && <Card title="Preparation Checklist"><ul className="space-y-2">{strategy.preparation_checklist.map((item, i) => <li key={i} className="flex items-start gap-2 text-sm text-gray-700"><span className="text-green-500 mt-0.5">☐</span>{item}</li>)}</ul></Card>}
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
    <div className="space-y-6">
      {error && <ErrorMessage message={error} />}
      <Card title="Career Goals">
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-gray-600">{goals.length} goal{goals.length !== 1 ? "s" : ""}</p>
          <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "+ New Goal"}</Button>
        </div>
        {showForm && (
          <form onSubmit={handleCreateGoal} className="space-y-4 border-t border-gray-200 pt-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Goal Title *</label><input type="text" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="e.g. Get promoted to Senior Engineer" /></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Target Date *</label><input type="date" required value={form.target_date} onChange={(e) => setForm({ ...form, target_date: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" /></div>
            </div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Description *</label><textarea required rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="Describe what you want to achieve..." /></div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Target Role</label><input type="text" value={form.target_role} onChange={(e) => setForm({ ...form, target_role: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="e.g. Staff Engineer" /></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Target Skills (comma separated)</label><input type="text" value={form.target_skills} onChange={(e) => setForm({ ...form, target_skills: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="e.g. System Design, Leadership" /></div>
            </div>
            <Button type="submit" loading={creating}>Create Goal</Button>
          </form>
        )}
      </Card>

      {goals.length === 0 ? (
        <Card><p className="text-gray-500 text-center py-8">No career goals yet. Create one to start tracking.</p></Card>
      ) : (
        <div className="space-y-4">
          {goals.map((goal) => (
            <Card key={goal.id}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-medium text-gray-900">{goal.title}</h3>
                  <p className="text-sm text-gray-600 mt-1">{goal.description}</p>
                  <div className="flex flex-wrap gap-3 mt-2 text-xs text-gray-500">
                    {goal.target_date && <span>📅 {new Date(goal.target_date).toLocaleDateString()}</span>}
                    {goal.target_role && <span>🎯 {goal.target_role}</span>}
                    {goal.progress !== undefined && <span>📊 {Math.round(goal.progress)}%</span>}
                  </div>
                </div>
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${goal.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                  {goal.is_active ? "Active" : "Done"}
                </span>
              </div>
              {goal.progress !== undefined && <div className="mt-3"><div className="h-2 bg-gray-100 rounded-full overflow-hidden"><div className="h-full bg-blue-500 rounded-full" style={{ width: `${Math.min(goal.progress, 100)}%` }} /></div></div>}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

export default Career;
