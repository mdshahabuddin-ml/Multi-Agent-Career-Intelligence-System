import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthContext } from "../context/AuthContext";
import { resumeService } from "../services";
import { atsService } from "../services";
import Button from "../components/common/Button";
import Card from "../components/common/Card";
import ErrorMessage from "../components/common/ErrorMessage";
import Loading from "../components/common/Loading";
import FileUpload from "../components/common/FileUpload";

function Resume() {
  const { user } = useAuthContext();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("upload");
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const [resumes, setResumes] = useState([]);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [selectedResume, setSelectedResume] = useState(null);

  const handleFileUpload = async (file) => {
    if (!file) return;
    
    setError("");
    setUploading(true);
    
    try {
      const formData = new FormData();
      formData.append("file", file);
      
      const response = await resumeService.uploadResume(file);
      const newResume = response.data;
      setResumes(prev => [newResume, ...prev]);
      setSelectedResume(newResume);
      setActiveTab("analyze");
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleAnalyze = async (resumeId) => {
    setError("");
    setAnalyzing(true);
    
    try {
      const result = await atsService.analyzeResume("", { resume_id: resumeId });
      setAnalysisResult(result);
    } catch (err) {
      setError(err.response?.data?.detail || "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleOptimize = async (resumeId, jobDescription) => {
    setError("");
    setAnalyzing(true);
    
    try {
      // Note: optimizeResume requires an application context
      // For now, we'll use the ATS analysis result as optimization suggestions
      const result = await atsService.analyzeResume("", { resume_id: resumeId, job_description: jobDescription });
      setAnalysisResult(prev => ({ ...prev, optimization: result }));
    } catch (err) {
      setError(err.response?.data?.detail || "Optimization failed");
    } finally {
      setAnalyzing(false);
    }
  };

  const fetchResumes = async () => {
    try {
      const response = await resumeService.listResumes();
      setResumes(response.data);
    } catch (err) {
      console.error("Failed to fetch resumes:", err);
    }
  };

  const tabs = [
    { id: "upload", label: "Upload Resume", icon: "📄" },
    { id: "analyze", label: "Analyze & Optimize", icon: "🔍" },
    { id: "manage", label: "My Resumes", icon: "📁" },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Resume Intelligence</h1>
          <p className="text-gray-600 mt-2">Upload, analyze, and optimize your resume with AI-powered insights</p>
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
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {/* Upload Tab */}
            {activeTab === "upload" && (
              <div className="max-w-2xl mx-auto">
                <FileUpload
                  onUpload={handleFileUpload}
                  loading={uploading}
                  accept=".pdf,.doc,.docx,.txt"
                  maxSize={10 * 1024 * 1024}
                  title="Upload Your Resume"
                  description="Supported formats: PDF, DOC, DOCX, TXT (max 10MB)"
                />
                
                <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                  <h3 className="font-medium text-blue-900 mb-2">Tips for best results:</h3>
                  <ul className="text-sm text-blue-800 space-y-1">
                    <li>• Use a clean, single-column format</li>
                    <li>• Include clear section headers (Experience, Education, Skills)</li>
                    <li>• Quantify achievements with numbers and metrics</li>
                    <li>• Include relevant keywords for your target role</li>
                  </ul>
                </div>
              </div>
            )}

            {/* Analyze Tab */}
            {activeTab === "analyze" && selectedResume && (
              <div className="max-w-4xl mx-auto">
                <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-medium text-gray-900">{selectedResume.original_filename || selectedResume.filename}</h3>
                      <p className="text-sm text-gray-500">Uploaded: {new Date(selectedResume.created_at).toLocaleDateString()}</p>
                    </div>
                    <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                      Ready for analysis
                    </span>
                  </div>
                </div>

                {analysisResult ? (
                  <AnalysisResults 
                    result={analysisResult} 
                    resumeId={selectedResume.id}
                    onOptimize={handleOptimize}
                    analyzing={analyzing}
                  />
                ) : (
                  <div className="text-center py-12">
                    <Card className="p-8">
                      <h3 className="text-lg font-medium text-gray-900 mb-2">Ready to Analyze</h3>
                      <p className="text-gray-600 mb-6">
                        Get AI-powered insights on your resume including ATS score, missing keywords, and optimization suggestions.
                      </p>
                      <Button 
                        onClick={() => handleAnalyze(selectedResume.id)}
                        loading={analyzing}
                        className="w-full"
                      >
                        Analyze Resume
                      </Button>
                    </Card>
                  </div>
                )}
              </div>
            )}

            {/* Manage Tab */}
            {activeTab === "manage" && (
              <div>
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-lg font-medium text-gray-900">My Resumes</h2>
                  <Button onClick={() => setActiveTab("upload")} variant="primary">
                    Upload New
                  </Button>
                </div>

                {resumes.length === 0 ? (
                  <div className="text-center py-12">
                    <Card className="p-8">
                      <p className="text-gray-500 mb-4">No resumes uploaded yet</p>
                      <Button onClick={() => setActiveTab("upload")} variant="primary">
                        Upload Your First Resume
                      </Button>
                    </Card>
                  </div>
                ) : (
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {resumes.map(resume => (
                      <ResumeCard 
                        key={resume.id} 
                        resume={resume}
                        onSelect={() => {
                          setSelectedResume(resume);
                          setActiveTab("analyze");
                        }}
                        onDelete={async () => {
                          if (confirm("Delete this resume?")) {
                            try {
                              await resumeService.deleteResume(resume.id);
                              setResumes(prev => prev.filter(r => r.id !== resume.id));
                            } catch (err) {
                              setError(err.response?.data?.detail || "Delete failed");
                            }
                          }
                        }}
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

function AnalysisResults({ result, resumeId, onOptimize, analyzing }) {
  const atsScore = result?.ats_analysis?.overall_score || 0;
  const scoreColor = atsScore >= 80 ? "text-green-600" : atsScore >= 60 ? "text-yellow-600" : "text-red-600";

  return (
    <div className="space-y-6">
      {/* ATS Score */}
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-medium text-gray-900">ATS Compatibility Score</h3>
            <p className="text-sm text-gray-500">How well your resume passes Applicant Tracking Systems</p>
          </div>
          <div className="text-right">
            <div className={`text-4xl font-bold ${scoreColor}`}>{atsScore}/100</div>
            <div className="text-sm text-gray-500">
              {atsScore >= 80 ? "Excellent" : atsScore >= 60 ? "Good" : "Needs Improvement"}
            </div>
          </div>
        </div>
      </Card>

      {/* Missing Keywords */}
      {result?.ats_analysis?.missing_keywords?.length > 0 && (
        <Card>
          <h3 className="font-medium text-gray-900 mb-4">Missing Keywords</h3>
          <p className="text-sm text-gray-500 mb-4">Add these keywords to improve ATS matching</p>
          <div className="flex flex-wrap gap-2">
            {result.ats_analysis.missing_keywords.slice(0, 15).map((keyword, i) => (
              <span key={i} className="px-3 py-1 text-sm bg-red-50 text-red-700 rounded-full border border-red-200">
                {keyword}
              </span>
            ))}
          </div>
        </Card>
      )}

      {/* Matched Keywords */}
      {result?.ats_analysis?.matched_keywords?.length > 0 && (
        <Card>
          <h3 className="font-medium text-gray-900 mb-4">Matched Keywords</h3>
          <p className="text-sm text-gray-500 mb-4">Good! These keywords are already in your resume</p>
          <div className="flex flex-wrap gap-2">
            {result.ats_analysis.matched_keywords.slice(0, 15).map((keyword, i) => (
              <span key={i} className="px-3 py-1 text-sm bg-green-50 text-green-700 rounded-full border border-green-200">
                {keyword}
              </span>
            ))}
          </div>
        </Card>
      )}

      {/* Recommendations */}
      {result?.ats_analysis?.recommendations?.length > 0 && (
        <Card>
          <h3 className="font-medium text-gray-900 mb-4">Optimization Recommendations</h3>
          <ul className="space-y-2">
            {result.ats_analysis.recommendations.map((rec, i) => (
              <li key={i} className="flex items-start text-sm text-gray-700">
                <span className="text-green-500 mr-2 mt-0.5">✓</span>
                {rec}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Optimization */}
      {result?.optimization && (
        <Card>
          <h3 className="font-medium text-gray-900 mb-4">Optimized Version</h3>
          <div className="bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap font-mono">
            {result.optimization.optimized_resume || JSON.stringify(result.optimization, null, 2)}
          </div>
          <div className="mt-4">
            <Button variant="secondary" onClick={() => navigator.clipboard.writeText(result.optimization.optimized_resume)}>
              Copy to Clipboard
            </Button>
          </div>
        </Card>
      )}

      {/* Job Description Optimization */}
      <Card>
        <h3 className="font-medium text-gray-900 mb-4">Optimize for Specific Job</h3>
        <p className="text-sm text-gray-500 mb-4">Paste a job description to get targeted optimizations</p>
        <JobOptimizationForm resumeId={resumeId} onOptimize={onOptimize} analyzing={analyzing} />
      </Card>
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
    <form onSubmit={handleSubmit} className="space-y-4">
      <textarea
        value={jobDescription}
        onChange={e => setJobDescription(e.target.value)}
        placeholder="Paste job description here..."
        rows={6}
        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        required
      />
      <Button type="submit" loading={analyzing} className="w-full">
        Optimize for This Job
      </Button>
    </form>
  );
}

function ResumeCard({ resume, onSelect, onDelete }) {
  return (
    <Card className="p-4 hover:shadow-md transition-shadow cursor-pointer" onClick={onSelect}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center">
          <span className="text-2xl mr-3">📄</span>
          <div>
            <h3 className="font-medium text-gray-900">{resume.original_filename || resume.filename}</h3>
            <p className="text-sm text-gray-500">
              {resume.file_size ? `${(resume.file_size / 1024).toFixed(1)} KB` : ''}
              • {new Date(resume.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
        <button
          onClick={e => { e.stopPropagation(); onDelete(); }}
          className="text-gray-400 hover:text-red-500 p-1"
          aria-label="Delete"
        >
          🗑️
        </button>
      </div>
      
      {resume.ats_score !== undefined && (
        <div className="pt-3 border-t border-gray-100">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-500">ATS Score</span>
            <span className={`font-medium ${resume.ats_score >= 80 ? 'text-green-600' : resume.ats_score >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
              {resume.ats_score}/100
            </span>
          </div>
        </div>
      )}
      
      <p className="mt-3 text-xs text-gray-400 text-center">Click to analyze</p>
    </Card>
  );
}

export default Resume;