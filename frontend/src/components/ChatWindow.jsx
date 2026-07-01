import React, { useState, useRef, useEffect } from "react";
import { Send, Paperclip, SendHorizontal, HelpCircle, FileSpreadsheet, Sparkles, User, Building, Phone, Mail, FileText, Mic, Square } from "lucide-react";

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
  sending, 
  activeSessionId 
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
          <Sparkles size={16} />
          <span>Digitized Contact Metadata</span>
        </div>
        
        {contact.name && (
          <div className="contact-row-item">
            <User size={14} style={{ color: "var(--accent-primary)" }} />
            <span><strong>Name:</strong> {contact.name}</span>
          </div>
        )}
        
        {contact.company && (
          <div className="contact-row-item">
            <Building size={14} style={{ color: "var(--accent-purple)" }} />
            <span><strong>Company:</strong> {contact.company}</span>
          </div>
        )}
        
        {contact.phone && (
          <div className="contact-row-item">
            <Phone size={14} style={{ color: "var(--accent-secondary)" }} />
            <span><strong>Phone:</strong> {contact.phone}</span>
          </div>
        )}
        
        {contact.email && (
          <div className="contact-row-item">
            <Mail size={14} style={{ color: "var(--accent-primary)" }} />
            <span><strong>Email:</strong> {contact.email}</span>
          </div>
        )}
        
        {contact.uuid && (
          <div className="contact-row-item">
            <FileText size={14} style={{ color: "var(--text-dark)" }} />
            <span style={{ fontSize: "0.75rem", fontFamily: "monospace" }}>
              <strong>UUID:</strong> {contact.uuid}
            </span>
          </div>
        )}
      </div>
    );
  };

  if (!activeSessionId) {
    return (
      <main className="chat-area">
        <div className="welcome-overlay">
          <h2 className="welcome-title">AI Digitization Hub</h2>
          <p className="welcome-desc">
            Orchestrate business card digitization and audio voice notes processing. 
            Create or select a chat session from the sidebar to begin.
          </p>
          
          <div className="feature-grid">
            <div className="feature-box">
              <Sparkles className="feature-box-icon" size={20} />
              <p className="feature-box-title">AI Business Card OCR</p>
              <p className="feature-box-desc">Upload card images to extract contact details using Gemini Flash.</p>
            </div>
            <div className="feature-box">
              <FileSpreadsheet className="feature-box-icon" size={20} />
              <p className="feature-box-title">Google Sheets Sync</p>
              <p className="feature-box-desc">Parsed cards are automatically written to a spreadsheet. Checks for duplicates.</p>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="chat-area">
      <header className="chat-header">
        <div className="chat-info">
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span className="font-display" style={{ fontSize: "1rem", fontWeight: "600" }}>Active Chat Session</span>
            <span style={{ fontSize: "0.75rem", color: "var(--text-dark)" }}>ID: {activeSessionId}</span>
          </div>
        </div>
        <div className="status-badge">
          <div className="status-dot status-online" />
          <span>Connected</span>
        </div>
      </header>

      <div className="message-window">
        {messages.length === 0 ? (
          <div className="welcome-overlay" style={{ padding: "80px 0" }}>
            <HelpCircle size={32} style={{ color: "var(--text-dark)", marginBottom: "8px" }} />
            <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
              Session initialized. Upload a visiting card image or type a message.
            </p>
          </div>
        ) : (
          messages.map((msg, index) => {
            const isUser = msg.sender === "user";
            const extractedContact = msg.metadata?.extracted_contact;
            
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
