import { useEffect, useState } from "react";
import { careerService } from "@services";
import Card from "../common/Card";
import Loading from "../common/Loading";
import ErrorMessage from "../common/ErrorMessage";
import Button from "../common/Button";

function LearningProgress() {
  const [learningPlan, setLearningPlan] = useState(null);
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchLearningData();
  }, []);

  const fetchLearningData = async () => {
    try {
      setLoading(true);
      // In a real app, this would fetch the user's current learning plan
      // For now, we'll show the empty state
    } catch (err) {
      setError("Failed to load learning progress");
    } finally {
      setLoading(false);
    }
  };

  const createLearningPlan = () => {
    // Navigate to career page to create a learning plan
    window.location.href = "/career";
  };

  if (loading) {
    return <Card><Loading /></Card>;
  }

  if (error) {
    return <Card><ErrorMessage message={error} /></Card>;
  }

  if (!learningPlan) {
    return (
      <Card title="Learning Progress" className="learning-progress">
        <div className="empty-state">
          <h3>No Active Learning Plan</h3>
          <p>Create a learning plan to track your skill development progress.</p>
          <Button variant="primary" onClick={createLearningPlan}>
            Create Learning Plan
          </Button>
        </div>
      </Card>
    );
  }

  // Extract milestones into a flat array for easier rendering
  const milestones = learningPlan?.phases?.flatMap(phase =>
    phase.milestones?.map((milestone, i) => ({
      ...milestone,
      phaseName: phase.name,
      phaseOrder: phase.order,
      milestoneOrder: i
    })) || []
  ) || [];

  return (
    <Card title="Learning Progress" className="learning-progress">
      <div className="progress-overview">
        <div className="progress-circle">
          <svg viewBox="0 0 120 120" className="progress-svg">
            <circle
              cx="60"
              cy="60"
              r="50"
              stroke="#e5e7eb"
              strokeWidth="10"
              fill="none"
            />
            <circle
              cx="60"
              cy="60"
              r="50"
              stroke="#3b82f6"
              strokeWidth="10"
              strokeDasharray={`${(progress?.completion_percentage || 0) / 100 * 314} 314`}
              strokeLinecap="round"
              fill="none"
              transform="rotate(-90 60 60)"
              className="progress-ring"
            />
          </svg>
          <div className="progress-text">
            <span className="progress-value">{progress?.completion_percentage || 0}%</span>
            <span className="progress-label">Complete</span>
          </div>
        </div>

        <div className="progress-stats">
          <div className="stat">
            <span className="stat-value">{progress?.completed_milestones || 0}</span>
            <span className="stat-label">Completed</span>
          </div>
          <div className="stat">
            <span className="stat-value">{progress?.total_milestones || 0}</span>
            <span className="stat-label">Total</span>
          </div>
          <div className="stat">
            <span className="stat-value">{progress?.completed_hours || 0}h</span>
            <span className="stat-label">Hours Spent</span>
          </div>
        </div>
      </div>

      <div className="current-phase">
        <h4>Current Phase: {learningPlan?.phases?.[progress?.current_phase]?.name || "None"}</h4>
        <div className="phase-progress">
          <div className="phase-bar">
            <div 
              className="phase-fill" 
              style={{ width: `${progress?.phase_progress || 0}%` }}
            />
          </div>
        </div>
      </div>

      <div className="milestones">
        <h4>Milestones</h4>
        <ul className="milestones-list">
          {milestones.map((milestone, index) => (
            <li key={index} className={`milestone-item ${milestone.is_completed ? "completed" : ""}`}>
              <div className="milestone-header">
                <span className="milestone-title">{milestone.title}</span>
                <span className={`milestone-status ${milestone.is_completed ? "completed" : "pending"}`}>
                  {milestone.is_completed ? "✓ Done" : `${milestone.estimated_weeks} weeks`}
                </span>
              </div>
              <div className="milestone-progress">
                <div className="progress-bar">
                  <div 
                    className="progress-fill" 
                    style={{ width: `${milestone.is_completed ? 100 : 0}%` }}
                  />
                </div>
              </div>
              {milestone.resources && milestone.resources.length > 0 && (
                <div className="milestone-resources">
                  {milestone.resources.slice(0, 3).map((resource, i) => (
                    <a 
                      key={i} 
                      href={resource.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="resource-link"
                    >
                      {resource.title} ({resource.resource_type})
                    </a>
                  ))}
                  {milestone.resources.length > 3 && (
                    <span className="more-resources">
                      +{milestone.resources.length - 3} more
                    </span>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>

      <div className="learning-actions">
        <Button variant="primary" disabled>
          Update Progress
        </Button>
        <Button variant="secondary" disabled>
          Adjust Plan
        </Button>
      </div>
    </Card>
  );
}

export default LearningProgress;