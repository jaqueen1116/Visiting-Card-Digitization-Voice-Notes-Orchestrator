import React, { useState, useRef, useEffect } from "react";
import { Send, Paperclip, SendHorizontal, HelpCircle, FileSpreadsheet, Sparkles, User, Building, Phone, Mail, FileText, Mic, Square, Home, Menu, UserCheck } from "lucide-react";

const parseMarkdown = (text) => {
  if (!text) return "";
  const lines = text.split("\n");
  return lines.map((line, idx) => {
    // Match bold markers **text**
    const boldRegex = /(\*\*.*?\*\*)/g;
    const parts = line.split(boldRegex);
    
    const renderedLine = parts.map((part, pIdx) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={pIdx}>{part.slice(2, -2)}</strong>;
      }
      
      // Match italic markers *text*
      const italicRegex = /(\*.*?\*)/g;
      const italicParts = part.split(italicRegex);
      return italicParts.map((iPart, iIdx) => {
        if (iPart.startsWith("*") && iPart.endsWith("*")) {
          return <em key={iIdx}>{iPart.slice(1, -1)}</em>;
        }
        return iPart;
      });
    });

    return (
      <div key={idx} style={{ minHeight: "1.2em" }}>
        {renderedLine}
      </div>
    );
  });
};

export default function ChatWindow({ 
  messages, 
  onSendMessage, 
  onOpenUploader, 
  onUploadFile,
  onBackToHome,
  sending, 
  activeSessionId,
  onToggleSidebar,
  onToggleRightPanel,
  hasActiveContact,
  mobileSidebarOpen,
  mobileRightPanelOpen,
  onCreateSession
}) {
  const [text, setText] = useState("");
  const messagesEndRef = useRef(null);

  // Audio recording states and references
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);

  // Start direct browser microphone recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const file = new File([audioBlob], "recorded_voice_note.webm", { type: "audio/webm" });
        if (onUploadFile) {
          onUploadFile(file);
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);

      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);

    } catch (err) {
      console.error("Error accessing microphone:", err);
      alert("Microphone permission denied or unavailable. Please enable mic access.");
    }
  };

  // Stop recording and release media tracks
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
      setIsRecording(false);
      
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  };

  // Clean up recording timers on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  const formatTime = (secs) => {
    const minutes = Math.floor(secs / 60);
    const seconds = secs % 60;
    return `${minutes}:${seconds < 10 ? "0" : ""}${seconds}`;
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, sending]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!text.trim() || sending) return;
    onSendMessage(text.trim());
    setText("");
  };

  const renderContactCard = (contact) => {
    if (!contact) return null;
    return (
      <div className="contact-card-embed">
        <div className="contact-header-title">
          <span>✓ Business Card Processed Successfully</span>
        </div>
        
        <div className="contact-details-grid">
          {contact.name && (
            <div className="contact-row-item">
              <span><strong>Name:</strong> {contact.name}</span>
            </div>
          )}
          
          {contact.company && (
            <div className="contact-row-item">
              <span><strong>Company:</strong> {contact.company}</span>
            </div>
          )}

          {contact.email && (
            <div className="contact-row-item">
              <span><strong>Email:</strong> {contact.email}</span>
            </div>
          )}
          
          {contact.phone && (
            <div className="contact-row-item">
              <span><strong>Phone:</strong> {contact.phone}</span>
            </div>
          )}
        </div>
      </div>
    );
  };

  if (!activeSessionId) {
    return (
      <main className="chat-area">
        <header className="chat-header">
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {/* Hamburger Menu Toggle for Mobile */}
            <button 
              type="button" 
              className={`icon-btn mobile-menu-btn ${mobileSidebarOpen ? "active" : ""}`}
              onClick={onToggleSidebar}
              title="Toggle Sessions List"
            >
              <Menu size={20} />
            </button>
            
            <div className="chat-info">
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span className="font-display" style={{ fontSize: "1rem", fontWeight: "600" }}>Krid Digitizer</span>
              </div>
            </div>
          </div>
          
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <button 
              type="button"
              className="icon-btn home-btn"
              onClick={onBackToHome}
              title="Go back to Homepage"
              style={{ 
                display: "flex", 
                alignItems: "center", 
                gap: "6px", 
                fontSize: "0.82rem", 
                padding: "6px 12px", 
                borderRadius: "10px", 
                border: "1px solid var(--border-color)", 
                background: "#FFFFFF",
                fontWeight: "600",
                color: "var(--text-main)",
                cursor: "pointer"
              }}
            >
              <Home size={14} />
              <span className="home-btn-text">Home</span>
            </button>
          </div>
        </header>

        <div className="welcome-overlay" style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <h1 className="welcome-title">Krid Orchestrator</h1>
          <p className="welcome-desc">
            A neat, light-mode orchestrator to digitize business cards, transcribe speech notes, dispatch notifications, and manage contacts seamlessly. Create a new chat session to get started.
          </p>
          
          <div className="feature-grid">
            <div className="feature-box lavender-box">
              <div className="feature-box-icon">
                <Sparkles size={24} style={{ color: "var(--accent-purple)" }} />
              </div>
              <h3 className="feature-box-title">AI Business Card OCR</h3>
              <p className="feature-box-desc">Upload card images to extract contact details using Gemini Flash.</p>
            </div>

            <div className="feature-box peach-box">
              <div className="feature-box-icon">
                <FileSpreadsheet size={24} style={{ color: "var(--accent-error)" }} />
              </div>
              <h3 className="feature-box-title">Google Sheets Sync</h3>
              <p className="feature-box-desc">Parsed cards are automatically written to a spreadsheet. Checks for duplicates.</p>
            </div>
          </div>

          {/* Primary CTA button to create a new session directly */}
          <div style={{ display: "flex", justifyContent: "center", marginTop: "32px" }}>
            <button
              type="button"
              className="primary-cta-btn"
              onClick={onCreateSession}
              style={{
                padding: "14px 28px",
                borderRadius: "12px",
                backgroundColor: "var(--accent-purple)",
                color: "#FFFFFF",
                fontWeight: "600",
                border: "none",
                cursor: "pointer",
                boxShadow: "var(--shadow-light)",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "0.95rem",
                transition: "all 0.2s"
              }}
            >
              <span>+ Create New Chat</span>
            </button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="chat-area">
      <header className="chat-header">
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {/* Hamburger Menu Toggle for Mobile */}
          <button 
            type="button" 
            className={`icon-btn mobile-menu-btn ${mobileSidebarOpen ? "active" : ""}`}
            onClick={onToggleSidebar}
            title="Toggle Sessions List"
          >
            <Menu size={20} />
          </button>
          
          <div className="chat-info">
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span className="font-display chat-title-desktop" style={{ fontSize: "1rem", fontWeight: "600" }}>Active Chat Session</span>
              <span className="font-display chat-title-mobile" style={{ fontSize: "1rem", fontWeight: "600" }}>Krid Digitizer</span>
              <span className="chat-subtitle-desktop" style={{ fontSize: "0.75rem", color: "var(--text-dark)" }}>ID: {activeSessionId}</span>
            </div>
          </div>
        </div>
        
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {/* Contact Profile Toggle for Mobile */}
          {hasActiveContact && (
            <button 
              type="button" 
              className={`icon-btn mobile-profile-btn ${mobileRightPanelOpen ? "active" : ""}`}
              onClick={onToggleRightPanel}
              title="Toggle Contact Profile"
            >
              <UserCheck size={20} />
            </button>
          )}

          <button 
            type="button"
            className="icon-btn home-btn"
            onClick={onBackToHome}
            title="Go back to Homepage"
            style={{ 
              display: "flex", 
              alignItems: "center", 
              gap: "6px", 
              fontSize: "0.82rem", 
              padding: "6px 12px", 
              borderRadius: "10px", 
              border: "1px solid var(--border-color)", 
              background: "#FFFFFF",
              fontWeight: "600",
              color: "var(--text-main)",
              cursor: "pointer"
            }}
          >
            <Home size={14} />
            <span className="home-btn-text">Home</span>
          </button>
          
          <div className="status-badge">
            <div className="status-dot status-online" />
            <span>Connected</span>
          </div>
        </div>
      </header>

      <div className="message-window">
        {messages.length === 0 ? (
          <div className="welcome-overlay">
            <h1 className="welcome-title">Krid Orchestrator</h1>
            <p className="welcome-desc">
              A neat, light-mode orchestrator to digitize business cards, transcribe speech notes, dispatch notifications, and manage contacts.
            </p>
            
            <div className="feature-grid dashboard-grid">
              <div className="feature-box upload-box" onClick={onOpenUploader} style={{ cursor: "pointer" }}>
                <div className="feature-box-icon">
                  <Paperclip size={24} style={{ color: "var(--accent-primary)" }} />
                </div>
                <h3 className="feature-box-title">Upload Business Card</h3>
                <p className="feature-box-desc">Drag & drop or click to upload business card image</p>
              </div>

              <div className="feature-box record-box" onClick={startRecording} style={{ cursor: "pointer" }}>
                <div className="feature-box-icon">
                  <Mic size={24} style={{ color: "var(--accent-secondary)" }} />
                </div>
                <h3 className="feature-box-title">Record Voice Note</h3>
                <p className="feature-box-desc">Record your voice notes quickly and easily directly in-browser</p>
              </div>

              <div className="feature-box lavender-box">
                <div className="feature-box-icon">
                  <FileText size={24} style={{ color: "var(--accent-purple)" }} />
                </div>
                <h3 className="feature-box-title">All in One Place</h3>
                <p className="feature-box-desc">Manage contacts, notes, and voice notes seamlessly</p>
              </div>

              <div className="feature-box peach-box">
                <div className="feature-box-icon">
                  <Sparkles size={24} style={{ color: "var(--accent-error)" }} />
                </div>
                <h3 className="feature-box-title">Stay Organized</h3>
                <p className="feature-box-desc">Never miss a follow-up with smart notifications</p>
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg, index) => {
            const isUser = msg.sender === "user";
            const extractedContact = msg.metadata?.status !== "failed" ? msg.metadata?.extracted_contact : null;
            
            return (
              <div key={index} className={`message-row ${isUser ? "user" : "assistant"}`}>
                <div className="message-bubble">
                  {/* Parse and render basic Markdown inline */}
                  <div className="markdown-content">
                    {parseMarkdown(msg.text)}
                  </div>
                  
                  {/* Render structured contact card if present */}
                  {extractedContact && renderContactCard(extractedContact)}
                  
                  <span className="message-meta">
                    {isUser ? "You" : "Assistant"} • {new Date(msg.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                  </span>
                </div>
              </div>
            );
          })
        )}
        
        {sending && (
          <div className="message-row assistant">
            <div className="message-bubble" style={{ display: "flex", alignItems: "center", gap: "10px", padding: "12px 18px" }}>
              <div className="spinner" />
              <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <footer className="chat-footer">
        <form onSubmit={handleSubmit} className="input-container">
          <button 
            type="button" 
            className="icon-btn"
            onClick={onOpenUploader}
            disabled={sending || isRecording}
            title="Upload Media (Card Image/Voice Audio)"
          >
            <Paperclip size={20} />
          </button>

          {isRecording ? (
            <button 
              type="button" 
              className="icon-btn stop-rec-btn"
              onClick={stopRecording}
              style={{ color: "#ef4444" }}
              title="Stop Recording & Transcribe"
            >
              <Square size={20} />
            </button>
          ) : (
            <button 
              type="button" 
              className="icon-btn mic-rec-btn"
              onClick={startRecording}
              disabled={sending}
              title="Record Voice Note directly"
            >
              <Mic size={20} />
            </button>
          )}
          
          {isRecording ? (
            <div className="recording-indicator" style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, padding: "0 15px", color: "#ef4444", fontSize: "0.9rem", fontWeight: "600" }}>
              <div className="pulse-dot" style={{ width: "10px", height: "10px", borderRadius: "50%", backgroundColor: "#ef4444" }} />
              <span>Recording Voice Note... ({formatTime(recordingTime)})</span>
            </div>
          ) : (
            <input 
              type="text" 
              className="chat-input"
              placeholder="Type a message or query contact details..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              disabled={sending}
            />
          )}
          
          <button 
            type="submit" 
            className="icon-btn send-btn"
            disabled={!text.trim() || sending || isRecording}
            title="Send Message"
          >
            <SendHorizontal size={18} />
          </button>
        </form>
      </footer>
    </main>
  );
}
