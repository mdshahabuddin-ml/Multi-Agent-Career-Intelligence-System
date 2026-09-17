import { useState, useRef } from "react";
import Button from "./Button";

const FileUpload = ({
  onUpload,
  loading = false,
  accept = "*/*",
  maxSize = 10 * 1024 * 1024,
  title = "Upload File",
  description = "",
  submitLabel = "Upload File",
  className = "",
}) => {
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const validateAndSet = (selectedFile) => {
    if (!selectedFile) return;

    if (selectedFile.size > maxSize) {
      setError(`File size exceeds ${(maxSize / (1024 * 1024)).toFixed(1)} MB limit`);
      setFile(null);
      return;
    }

    setError("");
    setFile(selectedFile);
  };

  const handleFileChange = (e) => {
    validateAndSet(e.target.files[0]);
    e.target.value = "";
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!loading) setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (loading) return;
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) validateAndSet(droppedFile);
  };

  const handleClick = () => {
    if (!loading) fileInputRef.current?.click();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a file");
      return;
    }
    await onUpload(file);
    setFile(null);
  };

  return (
    <div
      className={`resume-drop ${file ? "has-file" : ""} ${isDragging ? "dragging" : ""} ${className}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleFileChange}
        className="resume-drop-input"
        disabled={loading}
        aria-label={title}
      />
      <div
        className="resume-drop-zone"
        onClick={handleClick}
        role="button"
        tabIndex={loading ? -1 : 0}
        aria-disabled={loading}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") handleClick(); }}
      >
        <div className="resume-drop-icon" aria-hidden="true">⬆</div>
        <div>
          <h3>{title}</h3>
          {description && <p className="resume-drop-desc">{description}</p>}
          <p className="resume-drop-hint">Drag &amp; drop your file here, or click to browse</p>
        </div>
      </div>

      {file && (
        <div className="resume-drop-file">
          <div className="resume-drop-file-info">
            <span className="resume-drop-file-icon" aria-hidden="true">✓</span>
            <div>
              <p className="resume-drop-file-name">{file.name}</p>
              <p className="resume-drop-file-size">{(file.size / 1024).toFixed(1)} KB · ready to upload</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setFile(null)}
            className="resume-iconbtn"
            aria-label="Remove selected file"
          >
            ✕
          </button>
        </div>
      )}

      {error && (
        <p className="resume-drop-error" role="alert">{error}</p>
      )}

      <form onSubmit={handleSubmit} className="resume-drop-form">
        <Button type="submit" loading={loading} disabled={!file || loading}>
          {loading ? "Uploading…" : submitLabel}
        </Button>
      </form>
    </div>
  );
};

export default FileUpload;
