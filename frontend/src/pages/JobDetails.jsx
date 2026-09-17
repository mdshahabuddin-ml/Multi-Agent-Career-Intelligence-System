import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { jobSearchService } from "../services";
import Button from "../components/common/Button";
import Card from "../components/common/Card";
import ErrorMessage from "../components/common/ErrorMessage";
import Loading from "../components/common/Loading";

function JobDetails() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    jobSearchService.getJob(jobId)
      .then(response => {
        if (active) setJob(response?.data ?? response);
      })
      .catch(err => {
        if (active) setError(err.response?.data?.detail || err.message || "Failed to load job details");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [jobId]);

  if (loading) return <Loading />;

  return (
    <div className="page">
      <div className="page-header">
        <Button onClick={() => navigate(-1)}>Back to Jobs</Button>
        <h1>{job?.title || "Job Details"}</h1>
        {job && <p>{job.company_name || "Company not specified"} · {job.location || "Remote"}</p>}
      </div>

      {error && <ErrorMessage message={error} />}
      {job && (
        <Card>
          <div className="card-body">
            <div className="job-card-meta">
              {job.employment_type && <span>{job.employment_type}</span>}
              {job.experience_level && <span>{job.experience_level}</span>}
              {job.is_remote && <span>Remote</span>}
              {job.posted_date && <span>Posted {new Date(job.posted_date).toLocaleDateString()}</span>}
            </div>
            {job.skills?.length > 0 && <div className="job-card-tags">{job.skills.map(skill => <span key={skill} className="job-tag">{skill}</span>)}</div>}
            {job.description && <section><h2>Description</h2><p>{job.description}</p></section>}
            {job.requirements && <section><h2>Requirements</h2><p>{job.requirements}</p></section>}
            {job.responsibilities && <section><h2>Responsibilities</h2><p>{job.responsibilities}</p></section>}
            {(job.application_url || job.source_url) && (
              <a className="btn btn-primary" href={job.application_url || job.source_url} target="_blank" rel="noreferrer">Apply on source site</a>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}

export default JobDetails;