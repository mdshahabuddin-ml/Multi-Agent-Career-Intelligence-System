import { useState, useRef } from "react";
import Button from "./Button";

const FileUpload = ({
  onUpload,
  loading = false,
  accept = "*/*",
  maxSize = 10 * 1024 * 1024,
  title = "Upload File",
  description = "",
  className = "",
}) => {
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;

    if (selectedFile.size > maxSize) {
      setError(`File size exceeds ${(maxSize / (1024 * 1024)).toFixed(1)}MB limit`);
      setFile(null);
      return;
    }

    setError("");
    setFile(selectedFile);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileChange({ target: { files: [droppedFile] } });
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
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
    <div className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${className} ${file ? 'border-green-500 bg-green-50' : 'border-gray-300 hover:border-blue-500'}`}>
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleFileChange}
        className="hidden"
        id="file-upload"
        disabled={loading}
      />
      <label htmlFor="file-upload" className="cursor-pointer" onClick={handleClick}>
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 mx-auto rounded-full bg-blue-100 flex items-center justify-center">
            <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-medium text-gray-900">{title}</h3>
            {description && <p className="text-sm text-gray-500 mt-1">{description}</p>}
            <p className="text-xs text-gray-400 mt-2">Drag & drop or click to browse</p>
          </div>
        </div>
      </label>

      {file && (
        <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200 text-left">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p className="font-medium text-green-800">{file.name}</p>
                <p className="text-sm text-green-600">{(file.size / 1024).toFixed(1)} KB</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setFile(null)}
              className="text-gray-400 hover:text-red-500 transition-colors"
              aria-label="Remove file"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {error && (
        <p className="mt-3 text-sm text-red-600" role="alert">{error}</p>
      )}

      <form onSubmit={handleSubmit} className="mt-6">
        <Button type="submit" loading={loading} variant="primary" disabled={!file || loading} className="w-full">
          {loading ? "Uploading..." : "Upload File"}
        </Button>
      </form>
    </div>
  );
};

export default FileUpload;