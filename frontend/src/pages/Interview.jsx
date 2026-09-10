import { useState, useEffect, useCallback, useRef } from "react";
import { interviewService } from "../services";
import Card from "../components/common/Card";
import Loading from "../components/common/Loading";
import ErrorMessage from "../components/common/ErrorMessage";
import Button from "../components/common/Button";

function Interview() {
  const [activeTab, setActiveTab] = useState("practice");

  const tabs = [
    { id: "practice", label: "Mock Interview", icon: "🎙" },
    { id: "selfintro", label: "Self Introduction", icon: "👋" },
    { id: "star", label: "STAR Stories", icon: "⭐" },
    { id: "history", label: "History", icon: "📋" },
  ];

  return (
    <div className="page">
      <div className="page-header">
        <h1>Interview Intelligence</h1>
        <p>Practice interviews, master the STAR method, and polish your self-introduction</p>
      </div>

      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-1 -mb-px overflow-x-auto">
          {tabs.map((tab) => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${activeTab === tab.id ? "border-blue-500 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"}`}>
              <span className="mr-1">{tab.icon}</span>{tab.label}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === "practice" && <MockInterviewTab />}
      {activeTab === "selfintro" && <SelfIntroTab />}
      {activeTab === "star" && <STARStoriesTab />}
      {activeTab === "history" && <InterviewHistoryTab />}
    </div>
  );
}

/* ============================================
   Mock Interview Tab
============================================ */

function MockInterviewTab() {
  const [phase, setPhase] = useState("setup");
  const [session, setSession] = useState(null);
  const [currentQ, setCurrentQ] = useState(0);
  const [answer, setAnswer] = useState("");
  const [evaluation, setEvaluation] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({ target_role: "", target_company: "", interview_type: "behavioral", num_questions: 5 });
  const textareaRef = useRef(null);

  const handleStart = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const data = await interviewService.startMockInterview({
        target_role: form.target_role,
        target_company: form.target_company || undefined,
        interview_type: form.interview_type,
        num_questions: form.num_questions,
      });
      setSession(data);
      setPhase("interview");
      setCurrentQ(0);
      setAnswer("");
      setEvaluation(null);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to start interview");
    }
  };

  const handleSubmitAnswer = async () => {
    if (!answer.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const data = await interviewService.submitMockAnswer({
        session_id: session.session_id,
        question_id: session.questions[currentQ].id,
        answer: answer.trim(),
      });
      setEvaluation(data.evaluation);
      if (data.is_complete) {
        setPhase("review");
        const endData = await interviewService.endMockInterview(session.session_id);
        setResults(endData);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to submit answer");
    } finally {
      setSubmitting(false);
    }
  };

  const handleNextQuestion = () => {
    setCurrentQ(prev => prev + 1);
    setAnswer("");
    setEvaluation(null);
    if (textareaRef.current) textareaRef.current.focus();
  };

  const handleRestart = () => {
    setPhase("setup");
    setSession(null);
    setCurrentQ(0);
    setAnswer("");
    setEvaluation(null);
    setResults(null);
    setError(null);
  };

  if (phase === "setup") {
    return (
      <div className="space-y-6">
        {error && <ErrorMessage message={error} />}
        <Card title="Start a Mock Interview">
          <p className="text-sm text-gray-600 mb-4">Practice answering interview questions and get instant feedback on your content, communication, confidence, structure, and clarity.</p>
          <form onSubmit={handleStart} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Target Role *</label><input type="text" required value={form.target_role} onChange={(e) => setForm({ ...form, target_role: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="e.g. Software Engineer" /></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Target Company</label><input type="text" value={form.target_company} onChange={(e) => setForm({ ...form, target_company: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="e.g. Google" /></div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Interview Type</label><select value={form.interview_type} onChange={(e) => setForm({ ...form, interview_type: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"><option value="behavioral">Behavioral</option><option value="technical">Technical</option><option value="mixed">Mixed</option></select></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Number of Questions</label><input type="number" min="1" max="15" value={form.num_questions} onChange={(e) => setForm({ ...form, num_questions: parseInt(e.target.value) || 5 })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" /></div>
            </div>
            <Button type="submit">Start Interview</Button>
          </form>
        </Card>

        {/* STAR Method Guide */}
        <Card title="STAR Method Guide">
          <p className="text-sm text-gray-600 mb-4">Use the STAR method to structure your answers for behavioral questions:</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-blue-50 rounded-lg"><p className="text-2xl font-bold text-blue-700">S</p><p className="text-sm font-medium text-gray-900 mt-1">Situation</p><p className="text-xs text-gray-500 mt-0.5">Set the scene</p></div>
            <div className="text-center p-4 bg-green-50 rounded-lg"><p className="text-2xl font-bold text-green-700">T</p><p className="text-sm font-medium text-gray-900 mt-1">Task</p><p className="text-xs text-gray-500 mt-0.5">Your responsibility</p></div>
            <div className="text-center p-4 bg-yellow-50 rounded-lg"><p className="text-2xl font-bold text-yellow-700">A</p><p className="text-sm font-medium text-gray-900 mt-1">Action</p><p className="text-xs text-gray-500 mt-0.5">What you did</p></div>
            <div className="text-center p-4 bg-purple-50 rounded-lg"><p className="text-2xl font-bold text-purple-700">R</p><p className="text-sm font-medium text-gray-900 mt-1">Result</p><p className="text-xs text-gray-500 mt-0.5">The outcome</p></div>
          </div>
        </Card>
      </div>
    );
  }

  if (phase === "interview" && session) {
    const question = session.questions[currentQ];
    return (
      <div className="space-y-6">
        {error && <ErrorMessage message={error} />}
        {/* Progress */}
        <Card>
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium text-gray-900">{session.title}</h3>
            <span className="text-sm text-gray-500">Question {currentQ + 1} of {session.total_questions}</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${((currentQ + 1) / session.total_questions) * 100}%` }} />
          </div>
        </Card>

        {/* Question */}
        <Card>
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">{question.category}</span>
              <span className={`px-2 py-0.5 text-xs rounded ${question.difficulty === "hard" ? "bg-red-100 text-red-700" : question.difficulty === "medium" ? "bg-yellow-100 text-yellow-700" : "bg-green-100 text-green-700"}`}>{question.difficulty}</span>
            </div>
            <h3 className="text-lg font-medium text-gray-900">{question.question}</h3>
            {question.tips && <p className="text-sm text-gray-500 mt-2 italic">💡 {question.tips}</p>}
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">Your Answer</label>
            <textarea ref={textareaRef} rows={8} value={answer} onChange={(e) => setAnswer(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 resize-y" placeholder="Type your answer here. Use the STAR method for behavioral questions..." />
            <p className="text-xs text-gray-400 mt-1">{answer.split(/\s+/).filter(Boolean).length} words</p>
          </div>

          <div className="flex gap-3">
            <Button onClick={handleSubmitAnswer} loading={submitting} disabled={!answer.trim()}>Submit Answer</Button>
          </div>
        </Card>

        {/* Evaluation */}
        {evaluation && (
          <Card title="Answer Evaluation">
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 mb-6">
              <ScoreCircle label="Overall" score={evaluation.score} />
              <ScoreCircle label="Content" score={evaluation.content_score} />
              <ScoreCircle label="Communication" score={evaluation.communication_score} />
              <ScoreCircle label="Confidence" score={evaluation.confidence_score} />
              <ScoreCircle label="Structure" score={evaluation.structure_score} />
            </div>

            {evaluation.strengths?.length > 0 && (
              <div className="mb-4"><h4 className="text-sm font-medium text-green-700 mb-2">Strengths</h4><ul className="space-y-1">{evaluation.strengths.map((s, i) => <li key={i} className="text-sm text-gray-700 flex items-start gap-2"><span className="text-green-500">✓</span>{s}</li>)}</ul></div>
            )}
            {evaluation.improvements?.length > 0 && (
              <div className="mb-4"><h4 className="text-sm font-medium text-yellow-700 mb-2">Areas to Improve</h4><ul className="space-y-1">{evaluation.improvements.map((s, i) => <li key={i} className="text-sm text-gray-700 flex items-start gap-2"><span className="text-yellow-500">⚠</span>{s}</li>)}</ul></div>
            )}
            {evaluation.mistakes?.length > 0 && (
              <div className="mb-4"><h4 className="text-sm font-medium text-red-700 mb-2">Mistakes</h4><ul className="space-y-1">{evaluation.mistakes.map((s, i) => <li key={i} className="text-sm text-gray-700 flex items-start gap-2"><span className="text-red-500">✗</span>{s}</li>)}</ul></div>
            )}
            {evaluation.sample_answer && (
              <div className="p-3 bg-blue-50 rounded-lg mb-4"><h4 className="text-sm font-medium text-blue-700 mb-1">Suggested Structure</h4><p className="text-sm text-gray-700 whitespace-pre-line">{evaluation.sample_answer}</p></div>
            )}
            <p className="text-sm text-gray-600 mb-4">{evaluation.feedback}</p>
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <span>Uses STAR: {evaluation.uses_star_method ? "✓ Yes" : "✗ No"}</span>
              <span>·</span>
              <span>{evaluation.word_count} words</span>
            </div>
            <Button className="mt-4" onClick={handleNextQuestion}>{currentQ + 1 < session.total_questions ? "Next Question →" : "See Results"}</Button>
          </Card>
        )}
      </div>
    );
  }

  if (phase === "review" && results) {
    return (
      <div className="space-y-6">
        <Card title="Interview Complete!">
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-blue-100 mb-3"><span className="text-3xl font-bold text-blue-700">{results.overall_score}</span></div>
            <p className="text-sm text-gray-500">Overall Score (out of 10)</p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 mb-6">
            <ScoreCircle label="Content" score={results.avg_content_score} />
            <ScoreCircle label="Communication" score={results.avg_communication_score} />
            <ScoreCircle label="Confidence" score={results.avg_confidence_score} />
            <ScoreCircle label="Structure" score={results.avg_structure_score} />
            <ScoreCircle label="Clarity" score={results.avg_clarity_score} />
          </div>
          <p className="text-sm text-gray-700 mb-4">{results.detailed_feedback}</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
            {results.strengths?.length > 0 && <div><h4 className="text-sm font-medium text-green-700 mb-2">Strengths</h4><ul className="space-y-1">{results.strengths.map((s, i) => <li key={i} className="text-sm text-gray-700">✓ {s}</li>)}</ul></div>}
            {results.improvement_areas?.length > 0 && <div><h4 className="text-sm font-medium text-yellow-700 mb-2">Improvement Areas</h4><ul className="space-y-1">{results.improvement_areas.map((s, i) => <li key={i} className="text-sm text-gray-700">⚠ {s}</li>)}</ul></div>}
          </div>
          <p className="text-sm text-gray-500">{results.questions_evaluated} questions answered · {results.duration_minutes} min</p>
          <Button className="mt-4" onClick={handleRestart}>Start New Interview</Button>
        </Card>
      </div>
    );
  }

  return null;
}

function ScoreCircle({ label, score }) {
  const color = score >= 7.5 ? "text-green-600" : score >= 5 ? "text-yellow-600" : "text-red-600";
  return (
    <div className="text-center">
      <div className={`text-2xl font-bold ${color}`}>{score?.toFixed(1) || "-"}</div>
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  );
}

/* ============================================
   Self Introduction Tab
============================================ */

function SelfIntroTab() {
  const [intros, setIntros] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({ target_role: "", target_company: "", experience_years: 3, key_skills: "", notable_achievements: "" });

  const handleGenerate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await interviewService.getSelfIntro({
        target_role: form.target_role,
        target_company: form.target_company || undefined,
        experience_years: form.experience_years,
        key_skills: form.key_skills ? form.key_skills.split(",").map(s => s.trim()).filter(Boolean) : undefined,
        notable_achievements: form.notable_achievements ? form.notable_achievements.split(",").map(s => s.trim()).filter(Boolean) : undefined,
      });
      setIntros(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to generate introductions");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {error && <ErrorMessage message={error} />}
      <Card title="Self-Introduction Coach">
        <p className="text-sm text-gray-600 mb-4">Get personalized self-introduction templates and coaching for your interviews.</p>
        <form onSubmit={handleGenerate} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Target Role *</label><input type="text" required value={form.target_role} onChange={(e) => setForm({ ...form, target_role: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="e.g. Software Engineer" /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Target Company</label><input type="text" value={form.target_company} onChange={(e) => setForm({ ...form, target_company: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="e.g. Google" /></div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Years of Experience</label><input type="number" min="0" max="50" value={form.experience_years} onChange={(e) => setForm({ ...form, experience_years: parseInt(e.target.value) || 0 })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Key Skills (comma separated)</label><input type="text" value={form.key_skills} onChange={(e) => setForm({ ...form, key_skills: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="e.g. React, Python, System Design" /></div>
          </div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">Notable Achievements (comma separated)</label><input type="text" value={form.notable_achievements} onChange={(e) => setForm({ ...form, notable_achievements: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="e.g. Led team of 5, Increased revenue by 30%" /></div>
          <Button type="submit" loading={loading}>Generate Introductions</Button>
        </form>
      </Card>

      {intros && (
        <div className="space-y-6">
          {intros.introductions?.map((intro, i) => (
            <Card key={i} title={intro.label}>
              <p className="text-sm text-gray-700 leading-relaxed">{intro.content}</p>
            </Card>
          ))}

          {intros.structure_guide && (
            <Card title="Structure Guide">
              <p className="text-sm text-gray-700 whitespace-pre-line">{intros.structure_guide}</p>
            </Card>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {intros.tips?.length > 0 && (
              <Card title="Tips">
                <ul className="space-y-2">{intros.tips.map((tip, i) => <li key={i} className="flex items-start gap-2 text-sm text-gray-700"><span className="text-blue-500 mt-0.5">💡</span>{tip}</li>)}</ul>
              </Card>
            )}
            {intros.common_mistakes?.length > 0 && (
              <Card title="Common Mistakes">
                <ul className="space-y-2">{intros.common_mistakes.map((m, i) => <li key={i} className="flex items-start gap-2 text-sm text-gray-700"><span className="text-red-500 mt-0.5">✗</span>{m}</li>)}</ul>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ============================================
   STAR Stories Tab
============================================ */

function STARStoriesTab() {
  const [stories, setStories] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({ experience_description: "", target_role: "", num_stories: 3 });

  const handleGenerate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await interviewService.getStarStories({
        experience_description: form.experience_description,
        target_role: form.target_role || undefined,
        num_stories: form.num_stories,
      });
      setStories(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to generate STAR stories");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {error && <ErrorMessage message={error} />}
      <Card title="STAR Story Generator">
        <p className="text-sm text-gray-600 mb-4">Describe your experiences and we'll generate structured STAR stories you can use in interviews.</p>
        <form onSubmit={handleGenerate} className="space-y-4">
          <div><label className="block text-sm font-medium text-gray-700 mb-1">Describe Your Experiences *</label><textarea required rows={4} value={form.experience_description} onChange={(e) => setForm({ ...form, experience_description: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 resize-y" placeholder="Describe your key professional experiences, challenges you've faced, and achievements. Separate different experiences with periods or new lines..." /></div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Target Role</label><input type="text" value={form.target_role} onChange={(e) => setForm({ ...form, target_role: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="e.g. Senior Engineer" /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Number of Stories</label><input type="number" min="1" max="10" value={form.num_stories} onChange={(e) => setForm({ ...form, num_stories: parseInt(e.target.value) || 3 })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" /></div>
          </div>
          <Button type="submit" loading={loading}>Generate Stories</Button>
        </form>
      </Card>

      {stories && (
        <div className="space-y-6">
          {stories.stories?.map((story, i) => (
            <Card key={i} title={`Story ${i + 1}`}>
              <div className="space-y-3">
                <div className="p-3 bg-blue-50 rounded-lg"><p className="text-xs font-medium text-blue-700 mb-1">Situation</p><p className="text-sm text-gray-700">{story.situation}</p></div>
                <div className="p-3 bg-green-50 rounded-lg"><p className="text-xs font-medium text-green-700 mb-1">Task</p><p className="text-sm text-gray-700">{story.task}</p></div>
                <div className="p-3 bg-yellow-50 rounded-lg"><p className="text-xs font-medium text-yellow-700 mb-1">Action</p><p className="text-sm text-gray-700">{story.action}</p></div>
                <div className="p-3 bg-purple-50 rounded-lg"><p className="text-xs font-medium text-purple-700 mb-1">Result</p><p className="text-sm text-gray-700">{story.result}</p></div>
              </div>
              {story.applicable_questions?.length > 0 && (
                <div className="mt-3"><p className="text-xs text-gray-500 mb-1">Applicable to:</p><div className="flex flex-wrap gap-1">{story.applicable_questions.map((q, j) => <span key={j} className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">{q}</span>)}</div></div>
              )}
            </Card>
          ))}

          {stories.tips?.length > 0 && (
            <Card title="STAR Story Tips">
              <ul className="space-y-2">{stories.tips.map((tip, i) => <li key={i} className="flex items-start gap-2 text-sm text-gray-700"><span className="text-blue-500 mt-0.5">💡</span>{tip}</li>)}</ul>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

/* ============================================
   Interview History Tab
============================================ */

function InterviewHistoryTab() {
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    async function fetch() {
      try {
        setLoading(true);
        const data = await interviewService.getSavedPrep();
        setInterviews(data);
      } catch (err) {
        if (err.name === "CanceledError" || err.name === "AbortError") return;
        setError(err.response?.data?.detail || err.message || "Failed to load history");
      } finally {
        setLoading(false);
      }
    }
    fetch();
    return () => controller.abort();
  }, []);

  const loadDetail = async (id) => {
    setSelectedId(id);
    setDetailLoading(true);
    try {
      const data = await interviewService.getFeedback(id);
      setDetail(data);
    } catch (err) {
      console.error("Failed to load detail:", err);
    } finally {
      setDetailLoading(false);
    }
  };

  if (loading) return <Card><Loading /></Card>;

  const completed = interviews.filter(i => i.status === "completed");
  const inProgress = interviews.filter(i => i.status === "in_progress");

  return (
    <div className="space-y-6">
      {error && <ErrorMessage message={error} />}

      {inProgress.length > 0 && (
        <Card title="In Progress">
          <div className="space-y-2">{inProgress.map(i => (
            <div key={i.id} className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
              <div><p className="font-medium text-gray-900">{i.title}</p><p className="text-xs text-gray-500">{i.questions_count} questions · {i.interview_type}</p></div>
              <span className="px-2 py-0.5 text-xs bg-yellow-100 text-yellow-700 rounded">In Progress</span>
            </div>
          ))}</div>
        </Card>
      )}

      <Card title="Completed Interviews">
        {completed.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No completed interviews yet. Start a mock interview to see your history here.</p>
        ) : (
          <div className="space-y-3">
            {completed.map(i => (
              <div key={i.id} className={`p-4 border rounded-lg cursor-pointer transition-colors ${selectedId === i.id ? "border-blue-300 bg-blue-50" : "border-gray-200 hover:border-gray-300"}`} onClick={() => loadDetail(i.id)}>
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-gray-900">{i.title}</h4>
                    <p className="text-xs text-gray-500 mt-0.5">{i.questions_count} questions · {i.duration_minutes || "?"} min</p>
                  </div>
                  <div className="text-right">
                    {i.overall_score !== null && <p className={`text-lg font-bold ${i.overall_score >= 7.5 ? "text-green-600" : i.overall_score >= 5 ? "text-yellow-600" : "text-red-600"}`}>{i.overall_score}</p>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {detailLoading && <Card><Loading message="Loading feedback..." /></Card>}

      {detail && !detailLoading && (
        <Card title={detail.title}>
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-blue-100 mb-2"><span className="text-2xl font-bold text-blue-700">{detail.overall_score}</span></div>
            <p className="text-sm text-gray-500">Overall Score</p>
            {detail.duration_minutes && <p className="text-xs text-gray-400">{detail.duration_minutes} minutes</p>}
          </div>

          {detail.feedback && <p className="text-sm text-gray-700 mb-4">{detail.feedback}</p>}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
            {detail.strengths?.length > 0 && <div><h4 className="text-sm font-medium text-green-700 mb-2">Strengths</h4><ul className="space-y-1">{detail.strengths.map((s, i) => <li key={i} className="text-sm text-gray-700">✓ {s}</li>)}</ul></div>}
            {detail.improvement_areas?.length > 0 && <div><h4 className="text-sm font-medium text-yellow-700 mb-2">Improvement Areas</h4><ul className="space-y-1">{detail.improvement_areas.map((s, i) => <li key={i} className="text-sm text-gray-700">⚠ {s}</li>)}</ul></div>}
          </div>

          {detail.evaluations?.length > 0 && (
            <div><h4 className="text-sm font-medium text-gray-900 mb-3">Question Breakdown</h4>
              <div className="space-y-3">{detail.evaluations.map((ev, i) => (
                <div key={i} className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-sm font-medium text-gray-900 mb-1">{detail.questions?.[i]?.question || `Question ${i + 1}`}</p>
                  <div className="flex gap-4 text-xs text-gray-500">
                    <span>Score: {ev.score}/10</span>
                    <span>Content: {ev.content_score}</span>
                    <span>Structure: {ev.structure_score}</span>
                    <span>STAR: {ev.uses_star_method ? "✓" : "✗"}</span>
                  </div>
                </div>
              ))}</div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

export default Interview;
