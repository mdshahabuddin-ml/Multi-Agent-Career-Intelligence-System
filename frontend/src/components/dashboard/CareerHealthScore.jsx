import { useEffect, useState } from "react";
import { careerService } from "../../services";
import Card from "../common/Card";
import Loading from "../common/Loading";
import ErrorMessage from "../common/ErrorMessage";

function CareerHealthScore() {
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchInsights() {
      try {
        setLoading(true);
        const data = await careerService.getInsights();
        setInsights(data);
      } catch (err) {
        setError("Failed to load career insights");
      } finally {
        setLoading(false);
      }
    }

    fetchInsights();
  }, []);

  if (loading) {
    return (
      <Card>
        <Loading />
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <ErrorMessage message={error} />
      </Card>
    );
  }

  if (!insights) {
    return (
      <Card>
        <p className="text-gray-500">No career insights available yet.</p>
      </Card>
    );
  }

  const score = insights.overall_score || 0;
  const getScoreColor = (score) => {
    if (score >= 80) return "text-green-600";
    if (score >= 60) return "text-yellow-600";
    if (score >= 40) return "text-orange-600";
    return "text-red-600";
  };

  const getScoreLabel = (score) => {
    if (score >= 80) return "Excellent";
    if (score >= 60) return "Good";
    if (score >= 40) return "Fair";
    return "Needs Improvement";
  };

  return (
    <Card title="Career Health Score" className="career-health-score">
      <div className="health-score-container">
        <div className="score-circle">
          <svg viewBox="0 0 120 120" className="score-svg">
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
              stroke={getScoreColor(insights.overall_score)}
              strokeWidth="10"
              strokeDasharray={`${(insights.overall_score / 100) * 314} 314`}
              strokeLinecap="round"
              fill="none"
              transform="rotate(-90 60 60)"
              className="score-progress"
            />
          </svg>
          <div className="score-text">
            <span className={`score-value ${getScoreColor(insights.overall_score)}`}>
              {insights.overall_score}
            </span>
            <span className="score-label">{getScoreLabel(insights.overall_score)}</span>
          </div>
        </div>

        <div className="metrics-grid">
          <div className="metric-item">
            <span className="metric-value">{insights.total_skills || 0}</span>
            <span className="metric-label">Total Skills</span>
          </div>
          <div className="metric-item">
            <span className="metric-value">{Object.keys(insights.skill_categories || {}).length}</span>
            <span className="metric-label">Categories</span>
          </div>
          <div className="metric-item">
            <span className="metric-value">{insights.market_demand ? Math.round(insights.market_demand * 100) + '%' : 'N/A'}</span>
            <span className="metric-label">Market Demand</span>
          </div>
          <div className="metric-item">
            <span className="metric-value">
              ${insights.salary_estimate?.median ? (insights.salary_estimate.median / 1000).toFixed(0) + 'k' : 'N/A'}
            </span>
            <span className="metric-label">Est. Salary</span>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default CareerHealthScore;