import { useState, useEffect, useRef } from "react";
import { interviewService } from "../services";
import Card from "../components/common/Card";
import Loading from "../components/common/Loading";
import ErrorMessage from "../components/common/ErrorMessage";
import Button from "../components/common/Button";

function Interview() {
  const [activeTab, setActiveTab] = useState("practice");

  const tabs = [
    { id: "practice", label: "Mock Interview", icon: "🎙", desc: "Practice with live feedback" },
    { id: "selfintro", label: "Self Introduction", icon: "👋", desc: "Templates & coaching" },
    { id: "star", label: "STAR Stories", icon: "⭐", desc: "Structured story builder" },
    { id: "history", label: "History", icon: "📋", desc: "Past sessions & scores" },
  ];

  return (
    <div className="page interview-page">
      {/* Header */}
      <div className="interview-head">
        <div className="interview-head-text">
          <h1>Interview Intelligence</h1>
          <p>Practice interviews, master the STAR method, and polish your self-introduction.</p>
        </div>
        <div className="interview-ai-pill" title="Interview feedback is generated from your answers">
          <span className="interview-ai-dot" aria-hidden="true" />
          <span className="interview-ai-text">
            <strong>AI interview coach</strong>
            <small>Practice · feedback · review</small>
          </span>
        </div>
      </div>

      {/* Navigation cards */}
      <nav className="interview-nav" aria-label="Interview sections">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            aria-pressed={activeTab === tab.id}
            className={`interview-navcard ${activeTab === tab.id ? "active" : ""}`}
          >
            <span className="interview-navicon" aria-hidden="true">{tab.icon}</span>
            <span className="interview-navtext">
              <strong>{tab.label}</strong>
              <small>{tab.desc}</small>
            </span>
          </button>
        ))}
      </nav>

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
      <div className="interview-stack">
        {error && <ErrorMessage message={error} />}
        <Card title="Start a Mock Interview">
          <p className="interview-card-sub">Practice answering interview questions and get instant feedback on your content, communication, confidence, structure, and clarity.</p>
          <form onSubmit={handleStart} className="interview-form">
            <div className="interview-field-grid cols-2">
              <label className="interview-field">
                <span className="interview-field-label">Target Role *</span>
                <input type="text" required value={form.target_role} onChange={(e) => setForm({ ...form, target_role: e.target.value })} placeholder="e.g. Software Engineer" />
              </label>
              <label className="interview-field">
                <span className="interview-field-label">Target Company</span>
                <input type="text" value={form.target_company} onChange={(e) => setForm({ ...form, target_company: e.target.value })} placeholder="e.g. Google" />
              </label>
            </div>
            <div className="interview-field-grid cols-2">
              <label className="interview-field">
                <span className="interview-field-label">Interview Type</span>
                <select value={form.interview_type} onChange={(e) => setForm({ ...form, interview_type: e.target.value })}><option value="behavioral">Behavioral</option><option value="technical">Technical</option><option value="mixed">Mixed</option></select>
              </label>
              <label className="interview-field">
                <span className="interview-field-label">Number of Questions</span>
                <input type="number" min="1" max="15" value={form.num_questions} onChange={(e) => setForm({ ...form, num_questions: parseInt(e.target.value) || 5 })} />
              </label>
            </div>
            <div className="interview-actions-row">
              <Button type="submit">▶ Start Interview</Button>
            </div>
          </form>
        </Card>

        {/* STAR Method Guide */}
        <Card title="STAR Method Guide">
          <p className="interview-card-sub">Use the STAR method to structure your answers for behavioral questions:</p>
          <div className="interview-star-grid">
            <div className="interview-star-cell blue"><p className="interview-star-letter">S</p><p className="interview-star-name">Situation</p><p className="interview-star-desc">Set the scene</p></div>
            <div className="interview-star-cell green"><p className="interview-star-letter">T</p><p className="interview-star-name">Task</p><p className="interview-star-desc">Your responsibility</p></div>
            <div className="interview-star-cell amber"><p className="interview-star-letter">A</p><p className="interview-star-name">Action</p><p className="interview-star-desc">What you did</p></div>
            <div className="interview-star-cell purple"><p className="interview-star-letter">R</p><p className="interview-star-name">Result</p><p className="interview-star-desc">The outcome</p></div>
          </div>
        </Card>
      </div>
    );
  }

  if (phase === "interview" && session) {
    const question = session.questions[currentQ];
    const wordCount = answer.split(/\s+/).filter(Boolean).length;
    return (
      <div className="interview-stack">
        {error && <ErrorMessage message={error} />}
        {/* Progress */}
        <Card>
          <div className="interview-progress-head">
            <h3>{session.title}</h3>
            <span className="interview-muted">Question {currentQ + 1} of {session.total_questions}</span>
          </div>
          <div className="interview-bar-track">
            <div className="interview-bar-fill" style={{ width: `${((currentQ + 1) / session.total_questions) * 100}%` }} />
          </div>
        </Card>

        {/* Question */}
        <Card>
          <div className="interview-question">
            <div className="interview-chips">
              <span className="interview-chip chip-blue">{question.category}</span>
              <span className={`interview-chip ${question.difficulty === "hard" ? "chip-red" : question.difficulty === "medium" ? "chip-amber" : "chip-green"}`}>{question.difficulty}</span>
            </div>
            <h3 className="interview-question-text">{question.question}</h3>
            {question.tips && <p className="interview-tip">💡 {question.tips}</p>}
          </div>

          <label className="interview-field">
            <span className="interview-field-label">Your Answer</span>
            <textarea ref={textareaRef} rows={8} value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="Type your answer here. Use the STAR method for behavioral questions..." />
          </label>
          <p className="interview-wordcount">{wordCount} word{wordCount !== 1 ? "s" : ""}</p>

          <div className="interview-actions-row">
            <Button onClick={handleSubmitAnswer} loading={submitting} disabled={!answer.trim()}>{submitting ? "Evaluating…" : "Submit Answer"}</Button>
          </div>
        </Card>

        {/* Evaluation */}
        {evaluation && (
          <Card title="Answer Evaluation">
            <div className="interview-scores">
              <ScoreCircle label="Overall" score={evaluation.score} />
              <ScoreCircle label="Content" score={evaluation.content_score} />
              <ScoreCircle label="Communication" score={evaluation.communication_score} />
              <ScoreCircle label="Confidence" score={evaluation.confidence_score} />
              <ScoreCircle label="Structure" score={evaluation.structure_score} />
            </div>

            {evaluation.strengths?.length > 0 && (
              <div className="interview-feedback-block"><h4 className="good">Strengths</h4><ul className="interview-tick-list">{evaluation.strengths.map((s, i) => <li key={i} className="good"><span aria-hidden="true">✓</span>{s}</li>)}</ul></div>
            )}
            {evaluation.improvements?.length > 0 && (
              <div className="interview-feedback-block"><h4 className="warn">Areas to Improve</h4><ul className="interview-tick-list">{evaluation.improvements.map((s, i) => <li key={i} className="warn"><span aria-hidden="true">⚠</span>{s}</li>)}</ul></div>
            )}
            {evaluation.mistakes?.length > 0 && (
              <div className="interview-feedback-block"><h4 className="bad">Mistakes</h4><ul className="interview-tick-list">{evaluation.mistakes.map((s, i) => <li key={i} className="bad"><span aria-hidden="true">✗</span>{s}</li>)}</ul></div>
            )}
            {evaluation.sample_answer && (
              <div className="interview-sample"><h4>Suggested Structure</h4><p>{evaluation.sample_answer}</p></div>
            )}
            {evaluation.feedback && <p className="interview-feedback-text">{evaluation.feedback}</p>}
            <div className="interview-inline-meta">
              <span>Uses STAR: {evaluation.uses_star_method ? "✓ Yes" : "✗ No"}</span>
              <span>·</span>
              <span>{evaluation.word_count} words</span>
            </div>
            <div className="interview-actions-row">
              <Button onClick={handleNextQuestion}>{currentQ + 1 < session.total_questions ? "Next Question →" : "See Results"}</Button>
            </div>
          </Card>
        )}
      </div>
    );
  }

  if (phase === "review" && results) {
    return (
      <div className="interview-stack">
        <Card title="Interview Complete!">
          <div className="interview-review-hero">
            <div className="interview-score-ring">
              <span className="interview-score-value">{results.overall_score}</span>
              <span className="interview-score-max">/ 10</span>
            </div>
            <div className="interview-review-text">
              <h3>Overall Score</h3>
              <p>{results.questions_evaluated} questions answered · {results.duration_minutes} min</p>
            </div>
          </div>
          <div className="interview-scores">
            <ScoreCircle label="Content" score={results.avg_content_score} />
            <ScoreCircle label="Communication" score={results.avg_communication_score} />
            <ScoreCircle label="Confidence" score={results.avg_confidence_score} />
            <ScoreCircle label="Structure" score={results.avg_structure_score} />
            <ScoreCircle label="Clarity" score={results.avg_clarity_score} />
          </div>
          {results.detailed_feedback && <p className="interview-feedback-text">{results.detailed_feedback}</p>}
          <div className="interview-two-col">
            {results.strengths?.length > 0 && <div><h4 className="good">Strengths</h4><ul className="interview-tick-list">{results.strengths.map((s, i) => <li key={i} className="good"><span aria-hidden="true">✓</span>{s}</li>)}</ul></div>}
            {results.improvement_areas?.length > 0 && <div><h4 className="warn">Improvement Areas</h4><ul className="interview-tick-list">{results.improvement_areas.map((s, i) => <li key={i} className="warn"><span aria-hidden="true">⚠</span>{s}</li>)}</ul></div>}
          </div>
          <div className="interview-actions-row">
            <Button onClick={handleRestart}>↺ Start New Interview</Button>
          </div>
        </Card>
      </div>
    );
  }

  return null;
}

function ScoreCircle({ label, score }) {
  const tone = score >= 7.5 ? "good" : score >= 5 ? "warn" : "bad";
  return (
    <div className="interview-score">
      <div className={`interview-score-num ${tone}`}>{score?.toFixed(1) || "-"}</div>
      <p className="interview-score-label">{label}</p>
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
    <div className="interview-stack">
      {error && <ErrorMessage message={error} />}
      <Card title="Self-Introduction Coach">
        <p className="interview-card-sub">Get personalized self-introduction templates and coaching for your interviews.</p>
        <form onSubmit={handleGenerate} className="interview-form">
          <div className="interview-field-grid cols-2">
            <label className="interview-field">
              <span className="interview-field-label">Target Role *</span>
              <input type="text" required value={form.target_role} onChange={(e) => setForm({ ...form, target_role: e.target.value })} placeholder="e.g. Software Engineer" />
            </label>
            <label className="interview-field">
              <span className="interview-field-label">Target Company</span>
              <input type="text" value={form.target_company} onChange={(e) => setForm({ ...form, target_company: e.target.value })} placeholder="e.g. Google" />
            </label>
          </div>
          <div className="interview-field-grid cols-2">
            <label className="interview-field">
              <span className="interview-field-label">Years of Experience</span>
              <input type="number" min="0" max="50" value={form.experience_years} onChange={(e) => setForm({ ...form, experience_years: parseInt(e.target.value) || 0 })} />
            </label>
            <label className="interview-field">
              <span className="interview-field-label">Key Skills (comma separated)</span>
              <input type="text" value={form.key_skills} onChange={(e) => setForm({ ...form, key_skills: e.target.value })} placeholder="e.g. React, Python, System Design" />
            </label>
          </div>
          <label className="interview-field">
            <span className="interview-field-label">Notable Achievements (comma separated)</span>
            <input type="text" value={form.notable_achievements} onChange={(e) => setForm({ ...form, notable_achievements: e.target.value })} placeholder="e.g. Led team of 5, Increased revenue by 30%" />
          </label>
          <div className="interview-actions-row">
            <Button type="submit" loading={loading}>{loading ? "Generating…" : "Generate Introductions"}</Button>
          </div>
        </form>
      </Card>

      {intros && (
        <div className="interview-stack">
          {intros.introductions?.map((intro, i) => (
            <Card key={i} title={intro.label}>
              <p className="interview-body-text">{intro.content}</p>
            </Card>
          ))}

          {intros.structure_guide && (
            <Card title="Structure Guide">
              <p className="interview-preline">{intros.structure_guide}</p>
            </Card>
          )}

          <div className="interview-two-col">
            {intros.tips?.length > 0 && (
              <Card title="Tips">
                <ul className="interview-tick-list">{intros.tips.map((tip, i) => <li key={i} className="info"><span aria-hidden="true">💡</span>{tip}</li>)}</ul>
              </Card>
            )}
            {intros.common_mistakes?.length > 0 && (
              <Card title="Common Mistakes">
                <ul className="interview-tick-list">{intros.common_mistakes.map((m, i) => <li key={i} className="bad"><span aria-hidden="true">✗</span>{m}</li>)}</ul>
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
    <div className="interview-stack">
      {error && <ErrorMessage message={error} />}
      <Card title="STAR Story Generator">
        <p className="interview-card-sub">Describe your experiences and we&apos;ll generate structured STAR stories you can use in interviews.</p>
        <form onSubmit={handleGenerate} className="interview-form">
          <label className="interview-field">
            <span className="interview-field-label">Describe Your Experiences *</span>
            <textarea required rows={4} value={form.experience_description} onChange={(e) => setForm({ ...form, experience_description: e.target.value })} placeholder="Describe your key professional experiences, challenges you've faced, and achievements. Separate different experiences with periods or new lines..." />
          </label>
          <div className="interview-field-grid cols-2">
            <label className="interview-field">
              <span className="interview-field-label">Target Role</span>
              <input type="text" value={form.target_role} onChange={(e) => setForm({ ...form, target_role: e.target.value })} placeholder="e.g. Senior Engineer" />
            </label>
            <label className="interview-field">
              <span className="interview-field-label">Number of Stories</span>
              <input type="number" min="1" max="10" value={form.num_stories} onChange={(e) => setForm({ ...form, num_stories: parseInt(e.target.value) || 3 })} />
            </label>
          </div>
          <div className="interview-actions-row">
            <Button type="submit" loading={loading}>{loading ? "Generating…" : "Generate Stories"}</Button>
          </div>
        </form>
      </Card>

      {stories && (
        <div className="interview-stack">
          {stories.stories?.map((story, i) => (
            <Card key={i} title={`Story ${i + 1}${story.title ? ` — ${story.title}` : ""}`}>
              <div className="interview-star-story">
                <div className="interview-star-block blue"><p className="interview-star-block-label">Situation</p><p>{story.situation}</p></div>
                <div className="interview-star-block green"><p className="interview-star-block-label">Task</p><p>{story.task}</p></div>
                <div className="interview-star-block amber"><p className="interview-star-block-label">Action</p><p>{story.action}</p></div>
                <div className="interview-star-block purple"><p className="interview-star-block-label">Result</p><p>{story.result}</p></div>
              </div>
              {story.applicable_questions?.length > 0 && (
                <div className="interview-applicable">
                  <p className="interview-muted">Applicable to:</p>
                  <div className="interview-chips">
                    {story.applicable_questions.map((q, j) => <span key={j} className="interview-chip">{q}</span>)}
                  </div>
                </div>
              )}
            </Card>
          ))}

          {stories.tips?.length > 0 && (
            <Card title="STAR Story Tips">
              <ul className="interview-tick-list">{stories.tips.map((tip, i) => <li key={i} className="info"><span aria-hidden="true">💡</span>{tip}</li>)}</ul>
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
    <div className="interview-stack">
      {error && <ErrorMessage message={error} />}

      {inProgress.length > 0 && (
        <Card title="In Progress">
          <div className="interview-history-list">
            {inProgress.map(i => (
              <div key={i.id} className="interview-history-row progress">
                <div className="interview-history-main">
                  <p className="interview-history-title">{i.title}</p>
                  <p className="interview-muted">{i.questions_count} questions · {i.interview_type}</p>
                </div>
                <span className="interview-status-pill progress">In Progress</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card title="Completed Interviews">
        {completed.length === 0 ? (
          <div className="interview-empty slim">
            <h3>No history yet</h3>
            <p>No completed interviews yet. Start a mock interview to see your history here.</p>
          </div>
        ) : (
          <div className="interview-history-list">
            {completed.map(i => (
              <button
                key={i.id}
                onClick={() => loadDetail(i.id)}
                aria-pressed={selectedId === i.id}
                className={`interview-history-row clickable ${selectedId === i.id ? "selected" : ""}`}
              >
                <span className="interview-history-main">
                  <span className="interview-history-title">{i.title}</span>
                  <span className="interview-muted">{i.questions_count} questions · {i.duration_minutes || "?"} min</span>
                </span>
                {i.overall_score !== null && i.overall_score !== undefined && (
                  <span className={`interview-history-score ${i.overall_score >= 7.5 ? "good" : i.overall_score >= 5 ? "warn" : "bad"}`}>{i.overall_score}</span>
                )}
              </button>
            ))}
          </div>
        )}
      </Card>

      {detailLoading && <Card><Loading message="Loading feedback..." /></Card>}

      {detail && !detailLoading && (
        <Card title={detail.title}>
          <div className="interview-review-hero">
            <div className="interview-score-ring">
              <span className="interview-score-value">{detail.overall_score}</span>
              <span className="interview-score-max">/ 10</span>
            </div>
            <div className="interview-review-text">
              <h3>Overall Score</h3>
              {detail.duration_minutes && <p>{detail.duration_minutes} minutes</p>}
            </div>
          </div>

          {detail.feedback && <p className="interview-feedback-text">{detail.feedback}</p>}

          <div className="interview-two-col">
            {detail.strengths?.length > 0 && <div><h4 className="good">Strengths</h4><ul className="interview-tick-list">{detail.strengths.map((s, i) => <li key={i} className="good"><span aria-hidden="true">✓</span>{s}</li>)}</ul></div>}
            {detail.improvement_areas?.length > 0 && <div><h4 className="warn">Improvement Areas</h4><ul className="interview-tick-list">{detail.improvement_areas.map((s, i) => <li key={i} className="warn"><span aria-hidden="true">⚠</span>{s}</li>)}</ul></div>}
          </div>

          {detail.evaluations?.length > 0 && (
            <div>
              <p className="interview-section-label">Question Breakdown</p>
              <div className="interview-breakdown">
                {detail.evaluations.map((ev, i) => (
                  <div key={i} className="interview-breakdown-row">
                    <p className="interview-breakdown-q">{detail.questions?.[i]?.question || `Question ${i + 1}`}</p>
                    <div className="interview-breakdown-meta">
                      <span>Score: {ev.score}/10</span>
                      <span>Content: {ev.content_score}</span>
                      <span>Structure: {ev.structure_score}</span>
                      <span>STAR: {ev.uses_star_method ? "✓" : "✗"}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

export default Interview;
