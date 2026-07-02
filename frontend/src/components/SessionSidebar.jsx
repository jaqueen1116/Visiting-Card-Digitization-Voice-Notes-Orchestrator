import React from "react";
import { Plus, MessageSquare, Trash2, FolderSync } from "lucide-react";

export default function SessionSidebar({ 
  sessions, 
  activeSessionId, 
  onSelectSession, 
  onCreateSession, 
  onDeleteSession,
  loadingSessions
}) {
  return (
    <aside className="sidebar glass-panel">
      <div className="sidebar-header">
        <h1 className="sidebar-logo">
          <FolderSync size={24} />
          <span>Krid Orchestrator</span>
        </h1>
      </div>
      
      <button className="new-chat-btn" onClick={onCreateSession}>
        <Plus size={18} />
        <span>New Chat</span>
      </button>

      <div className="session-list">
        {loadingSessions ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "40px 0" }}>
            <div className="spinner" />
          </div>
        ) : sessions.length === 0 ? (
          <div style={{ textAlign: "center", color: "var(--text-dark)", padding: "40px 0", fontSize: "0.85rem" }}>
            No active sessions.
          </div>
        ) : (
          sessions.map((session) => {
            const isActive = session.session_id === activeSessionId;
            const contactLetter = session.contact_name 
              ? session.contact_name.charAt(0).toUpperCase()
              : "C";
              
            const displayTitle = session.contact_name 
              ? session.contact_name
              : "New Card Sync";
              
            const snippetText = session.last_contact_uuid
              ? "Business card processed"
              : "Session initialized...";

            const dateStr = session.updated_at
              ? new Date(session.updated_at).toLocaleDateString([], { month: "short", day: "numeric" })
              : "Today";
              
            return (
              <div 
                key={session.session_id} 
                className={`session-item ${isActive ? "active" : ""}`}
                onClick={() => onSelectSession(session.session_id)}
              >
                <div className="session-title-container">
                  <div className={`session-avatar-badge avatar-${contactLetter.toLowerCase()}`}>
                    {contactLetter}
                  </div>
                  <div className="session-text-group">
                    <span className="session-title">{displayTitle}</span>
                    <span className="session-snippet">{snippetText}</span>
                  </div>
                </div>
                
                <div className="session-meta-group">
                  <span className="session-date">{dateStr}</span>
                  <button 
                    className="delete-session-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(session.session_id);
                    }}
                    title="Delete Session"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Pro Tip Card at the bottom of the sidebar */}
      <div className="sidebar-pro-tip">
        <div className="pro-tip-header">
          <FolderSync size={20} className="pro-tip-icon" />
          <h4 className="pro-tip-title">Pro Tip</h4>
        </div>
        <p className="pro-tip-desc">Upload clear business card images for best results.</p>
        <button className="pro-tip-btn">Learn More</button>
      </div>
    </aside>
  );
}
