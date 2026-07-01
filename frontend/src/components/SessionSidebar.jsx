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
        <span>New Chat Session</span>
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
            const displayTitle = session.last_contact_uuid 
              ? `Contact: ${session.last_contact_uuid.substring(0, 8)}...`
              : `Session: ${session.session_id.substring(0, 8)}...`;
              
            return (
              <div 
                key={session.session_id} 
                className={`session-item ${isActive ? "active" : ""}`}
                onClick={() => onSelectSession(session.session_id)}
              >
                <div className="session-title-container">
                  <MessageSquare size={16} style={{ color: isActive ? "var(--accent-primary)" : "var(--text-dark)", flexShrink: 0 }} />
                  <span className="session-title">{displayTitle}</span>
                </div>
                
                <button 
                  className="delete-session-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteSession(session.session_id);
                  }}
                  title="Delete Session"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
