import { useEffect, useState } from "react";
import { useAuthContext } from "../context/AuthContext";
import { careerService, applicationService, jobSearchService } from "@services";
import Card from "../components/common/Card";
import Loading from "../components/common/Loading";
import ErrorMessage from "../components/common/ErrorMessage";
import CareerHealthScore from "../components/dashboard/CareerHealthScore";
import ApplicationTracker from "../components/dashboard/ApplicationTracker";
import CareerIntelligencePanel from "../components/dashboard/CareerIntelligencePanel";
import JobRecommendations from "../components/dashboard/JobRecommendations";
import ResearchPanel from "../components/dashboard/ResearchPanel";
import LearningProgress from "../components/dashboard/LearningProgress";

function Dashboard() {
  const { user } = useAuthContext();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(false);
  }, []);

  if (loading) {
    return <Loading />;
  }

  if (error) {
    return <ErrorMessage message={error} />;
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>
          Welcome back, {user?.full_name || "User"}! Your personalized career intelligence overview.
        </p>
      </div>

      {/* Career Health Score - Full Width */}
      <CareerHealthScore />

      {/* Main Grid */}
      <div className="dashboard-grid">
        {/* Left Column - 2/3 width */}
        <div className="dashboard-main">
          {/* Application Tracker */}
          <ApplicationTracker />

          {/* Career Intelligence Panel */}
          <CareerIntelligencePanel />

          {/* Learning Progress */}
          <LearningProgress />
        </div>

        {/* Right Sidebar - 1/3 width */}
        <div className="dashboard-sidebar">
          {/* Job Recommendations */}
          <JobRecommendations />

          {/* Research Panel */}
          <ResearchPanel />

          {/* Quick Actions */}
          <QuickActions />
        </div>
      </div>
    </div>
  );
}

function QuickActions() {
  return (
    <Card title="Quick Actions" className="quick-actions">
      <div className="actions-grid">
        <a href="/resume/upload" className="action-btn">
          <span className="action-icon">📄</span>
          <div>
            <span className="action-title">Upload Resume</span>
            <span className="action-desc">Upload and analyze your resume</span>
          </div>
        </a>
        <a href="/research" className="action-btn">
          <span className="action-icon">🔬</span>
          <div>
            <span className="action-title">Start Research</span>
            <span className="action-desc">Multi-agent research</span>
          </div>
        </a>
        <a href="/jobs" className="action-btn">
          <span className="action-icon">💼</span>
          <div>
            <span className="action-title">Browse Jobs</span>
            <span className="action-desc">Find opportunities</span>
          </div>
        </a>
        <a href="/career" className="action-btn">
          <span className="action-icon">📈</span>
          <div>
            <span className="action-title">Career Plan</span>
            <span className="action-desc">View career path</span>
          </div>
        </a>
        <a href="/applications" className="action-btn">
          <span className="action-icon">📋</span>
          <div>
            <span className="action-title">Applications</span>
            <span className="action-desc">Track applications</span>
          </div>
        </a>
        <a href="/interview" className="action-btn">
          <span className="action-icon">🎤</span>
          <div>
            <span className="action-title">Interview Prep</span>
            <span className="action-desc">Practice interviews</span>
          </div>
        </a>
      </div>
    </Card>
  );
}

export default Dashboard;