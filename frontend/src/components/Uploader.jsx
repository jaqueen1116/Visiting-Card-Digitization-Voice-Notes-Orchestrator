import React, { useState, useRef } from "react";
import { X, UploadCloud, FileImage, FileAudio, CheckCircle, AlertCircle } from "lucide-react";

export default function Uploader({ onClose, onUpload, uploading }) {
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (selectedFile) => {
    setError("");
    const type = selectedFile.type;
    const name = selectedFile.name.toLowerCase();
    
    const isImage = type.startsWith("image/");
    const isAudio = type.startsWith("audio/") || name.endsWith(".wav") || name.endsWith(".mp3") || name.endsWith(".m4a") || name.endsWith(".ogg") || name.endsWith(".webm");
    
    if (!isImage && !isAudio) {
      setError("Invalid file type. Please upload a Visiting Card (Image) or a Voice Note (Audio).");
      setFile(null);
      return;
    }
    
    setFile({
      native: selectedFile,
      name: selectedFile.name,
      size: (selectedFile.size / (1024 * 1024)).toFixed(2) + " MB",
      classType: isImage ? "image" : "audio"
    });
  };

  const triggerFileInput = () => {
    fileInputRef.current.click();
  };

  const handleUploadSubmit = () => {
    if (!file) return;
    onUpload(file.native);
  };

  return (
    <div className="uploader-overlay">
      <div className="uploader-panel glass-panel">
        <button className="icon-btn close-uploader-btn" onClick={onClose} disabled={uploading}>
          <X size={18} />
        </button>

        <h3 style={{ marginBottom: "20px", fontFamily: "var(--font-display)", fontSize: "1.1rem" }}>
          Upload Media File
        </h3>

        {!file ? (
          <div 
            className={`dropzone ${dragActive ? "dragover" : ""}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={triggerFileInput}
          >
            <input 
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              style={{ display: "none" }}
              accept="image/*,audio/*"
            />
            
            <UploadCloud size={40} style={{ color: "var(--accent-primary)" }} />
            
            <div className="dropzone-text">
              <p className="dropzone-title">Drag & drop your file here</p>
              <p className="dropzone-desc">Accepts business cards (images) or voice notes (audio)</p>
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div className="file-preview">
              <div className="file-info">
                {file.classType === "image" ? (
                  <FileImage size={24} style={{ color: "var(--accent-primary)" }} />
                ) : (
                  <FileAudio size={24} style={{ color: "var(--accent-secondary)" }} />
                )}
                <div>
                  <p className="file-name" title={file.name}>{file.name}</p>
                  <p className="file-size">{file.size} • {file.classType === "image" ? "Business Card" : "Voice Note"}</p>
                </div>
              </div>
              
              <button 
                className="icon-btn" 
                onClick={() => setFile(null)} 
                disabled={uploading}
                style={{ color: "var(--text-dark)" }}
              >
                <X size={16} />
              </button>
            </div>

            <button 
              className="upload-action-btn"
              onClick={handleUploadSubmit}
              disabled={uploading}
            >
              {uploading ? (
                <>
                  <div className="spinner" />
                  <span>Processing File...</span>
                </>
              ) : (
                <>
                  <CheckCircle size={18} />
                  <span>Submit to Orchestrator</span>
                </>
              )}
            </button>
          </div>
        )}

        {error && (
          <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--accent-error)", fontSize: "0.8rem", marginTop: "16px" }}>
            <AlertCircle size={14} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
}
