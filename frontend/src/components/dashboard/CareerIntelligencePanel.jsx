import { useEffect, useState } from "react";
import { careerService } from "../../services";
import Card from "../common/Card";
import Loading from "../common/Loading";
import ErrorMessage from "../common/ErrorMessage";

function CareerIntelligencePanel() {
  const [trajectory, setTrajectory] = useState(null);
  const [skillGaps, setSkillGaps] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("trajectory");

  useEffect(() => {
    const controller = new AbortController();

    async function fetchData() {
      try {
        setLoading(true);
        const [trajectoryData, gapData] = await Promise.all([
          careerService.getPathOptions("Software Engineer", controller.signal),
          careerService.getSkillRecommendations("Senior Software Engineer", controller.signal),
        ]);
        setTrajectory(trajectoryData);
        setSkillGaps(gapData);
      } catch (err) {
        if (err.name === "CanceledError" || err.name === "AbortError") return;
        const message = err.response?.data?.detail || err.message || "Failed to load career intelligence";
        setError(message);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
    return () => controller.abort();
  }, []);

  if (loading) {
    return <Card><Loading /></Card>;
  }

  if (error) {
    return <Card><ErrorMessage message={error} /></Card>;
  }

  return (
    <Card title="Career Intelligence" className="career-intelligence">
      <div className="intelligence-tabs">
        <button
          className={`tab-btn ${activeTab === "trajectory" ? "active" : ""}`}
          onClick={() => setActiveTab("trajectory")}
        >
          Career Paths
        </button>
        <button
          className={`tab-btn ${activeTab === "skills" ? "active" : ""}`}
          onClick={() => setActiveTab("skills")}
        >
          Skill Gaps
        </button>
        <button
          className={`tab-btn ${activeTab === "learning" ? "active" : ""}`}
          onClick={() => setActiveTab("learning")}
        >
          Learning Plan
        </button>
      </div>

      <div className="tab-content">
        {activeTab === "trajectory" && (
          <CareerTrajectoryView trajectory={trajectory} />
        )}
        {activeTab === "skills" && (
          <SkillGapsView skillGaps={skillGaps} />
        )}
        {activeTab === "learning" && (
          <LearningPlanView />
        )}
      </div>
    </Card>
  );
}

function CareerTrajectoryView({ trajectory }) {
  if (!trajectory || !trajectory.recommended_path) {
    return (
      <div className="empty-state">
        <p>No career trajectory data available yet.</p>
        <p className="text-sm text-gray-500">
          Complete your profile to see personalized career paths.
        </p>
      </div>
    );
  }

  const path = trajectory.recommended_path;

  return (
    <div className="trajectory-view">
      <div className="path-header">
        <h3>{path.target_role}</h3>
        <div className="path-meta">
          <span className="path-duration">
            ⏱ {path.total_estimated_time_months} months
          </span>
          <span className="path-growth">
            📈 +{path.total_salary_growth_pct}% salary growth
          </span>
        </div>
      </div>

      <div className="transitions">
        {path.transitions?.map((transition, index) => (
          <div key={index} className="transition-step">
            <div className="step-header">
              <span className="step-number">{index + 1}</span>
              <div className="step-info">
                <h4>{transition.to_role}</h4>
                <p className="step-type">
                  {transition.transition_type} • {transition.estimated_time_months} months
                </p>
              </div>
              <span className={`salary-change ${transition.salary_change_pct > 0 ? "positive" : "negative"}`}>
                {transition.salary_change_pct > 0 ? "+" : ""}{transition.salary_change_pct}%
              </span>
            </div>
            <div className="step-skills">
              <strong>Required Skills:</strong>
              <div className="skills-tags">
                {transition.required_additional_skills?.slice(0, 5).map((skill, i) => (
                  <span key={i} className="skill-tag">{skill}</span>
                ))}
              </div>
            </div>
            <div className="step-factors">
              <strong>Success Factors:</strong>
              <ul>
                {transition.success_factors?.slice(0, 3).map((factor, i) => (
                  <li key={i}>{factor}</li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>

      <div className="alternatives">
        <h4>Alternative Paths</h4>
        <div className="alt-paths">
          {trajectory.alternative_paths?.slice(0, 3).map((path, i) => (
            <div key={i} className="alt-path">
              <h5>{path.target_role}</h5>
              <p>{path.total_estimated_time_months} months • +{path.total_salary_growth_pct}% salary</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SkillGapsView({ skillGaps }) {
  if (!skillGaps || !skillGaps.gaps || skillGaps.gaps.length === 0) {
    return (
      <div className="empty-state">
        <p>No skill gap data available.</p>
      </div>
    );
  }

  const criticalGaps = skillGaps.gaps.filter(g => g.gap_severity > 0.7);
  const moderateGaps = skillGaps.gaps.filter(g => g.gap_severity > 0.4 && g.gap_severity <= 0.7);
  const minorGaps = skillGaps.gaps.filter(g => g.gap_severity <= 0.4);

  return (
    <div className="skill-gaps-view">
      <div className="gaps-summary">
        <div className="summary-card critical">
          <span className="count">{skillGaps.critical_gaps_count}</span>
          <span className="label">Critical Gaps</span>
        </div>
        <div className="summary-card moderate">
          <span className="count">{skillGaps.moderate_gaps_count}</span>
          <span className="label">Moderate Gaps</span>
        </div>
        <div className="summary-card minor">
          <span className="count">{skillGaps.minor_gaps_count}</span>
          <span className="label">Minor Gaps</span>
        </div>
      </div>

      <div className="gaps-list">
        <h4>Critical Gaps</h4>
        <ul className="gaps-list-items">
          {criticalGaps.slice(0, 5).map((gap, i) => (
            <li key={i} className="gap-item critical">
              <div className="gap-info">
                <h5>{gap.skill_name}</h5>
                <p>Required: {gap.required_proficiency} • Current: {gap.candidate_proficiency || "Missing"}</p>
              </div>
              <span className="severity critical">{Math.round(gap.gap_severity * 100)}%</span>
            </li>
          ))}
        </ul>

        <h4>Priority Skills to Learn</h4>
        <div className="priority-skills">
          {skillGaps.priority_skills?.slice(0, 5).map((skill, i) => (
            <span key={i} className="priority-tag">{skill}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

function LearningPlanView() {
  return (
    <div className="learning-plan-view">
      <p>Learning plan view coming soon...</p>
    </div>
  );
}

export default CareerIntelligencePanel;