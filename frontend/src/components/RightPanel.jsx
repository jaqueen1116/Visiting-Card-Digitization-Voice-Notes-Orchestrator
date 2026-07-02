import React from "react";
import { User, Sparkles, Phone, Mail, Building, Globe, MapPin, FileText, Download, Music } from "lucide-react";

export default function RightPanel({ activeContact, messages }) {
  // Find the latest audio message to show in the Voice Notes section of the panel
  const latestAudioMessage = [...messages]
    .reverse()
    .find(msg => msg.type === "audio" || msg.text?.includes("Voice Note"));

  // Check if we have active contact card details
  if (!activeContact) {
    return (
      <aside className="right-panel glass-panel placeholder">
        <div className="panel-placeholder-content">
          <div className="placeholder-card-icon">
            <Sparkles size={36} className="text-secondary" />
          </div>
          <h2 className="font-display placeholder-title">Directory Overview</h2>
          <p className="placeholder-desc">
            Digitise a business card to populate profiles, follow-up notes, file attachments, and voice transcript logs.
          </p>
          <div className="placeholder-visual-card">
            <div className="placeholder-line short" />
            <div className="placeholder-line" />
            <div className="placeholder-line medium" />
          </div>
        </div>
      </aside>
    );
  }

  return (
    <aside className="right-panel glass-panel">
      {/* 1. Contact Info Card */}
      <section className="panel-section">
        <h3 className="section-title">Contact Info</h3>
        <div className="contact-profile-card">
          <div className="profile-avatar">
            <User size={28} style={{ color: "var(--text-main)" }} />
          </div>
          <h4 className="font-display profile-name">{activeContact.name || "Unknown"}</h4>
          <span className="profile-company">{activeContact.company || "No Company Specified"}</span>
          
          <div className="profile-details-list">
            {activeContact.email && (
              <div className="profile-detail-item">
                <Mail size={14} className="detail-icon" />
                <span title={activeContact.email}>{activeContact.email}</span>
              </div>
            )}
            {activeContact.phone && (
              <div className="profile-detail-item">
                <Phone size={14} className="detail-icon" />
                <span>{activeContact.phone}</span>
              </div>
            )}
            {activeContact.company && (
              <div className="profile-detail-item">
                <Building size={14} className="detail-icon" />
                <span>{activeContact.company}</span>
              </div>
            )}
            <div className="profile-detail-item">
              <MapPin size={14} className="detail-icon" />
              <span>San Francisco, CA</span>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Notes Card */}
      <section className="panel-section">
        <h3 className="section-title">Notes</h3>
        <div className="panel-card peach-card">
          <p className="card-text">
            {activeContact.voice_notes || "Follow up next week regarding the proposal and pricing details."}
          </p>
          <span className="card-meta">Updated today</span>
        </div>
      </section>

      {/* 3. Files Card */}
      <section className="panel-section">
        <h3 className="section-title">Files</h3>
        <div className="panel-card lavender-card file-card">
          <div className="file-card-info">
            <div className="file-icon-box">
              <FileText size={16} />
            </div>
            <div className="file-meta">
              <span className="file-title">business_card.jpg</span>
              <span className="file-size">245 KB</span>
            </div>
          </div>
          <button className="file-download-btn" title="Download Card File">
            <Download size={14} />
          </button>
        </div>
      </section>

      {/* 4. Voice Notes Card */}
      <section className="panel-section">
        <h3 className="section-title">Voice Notes</h3>
        <div className="panel-card mint-card voice-note-card">
          <div className="voice-card-header">
            <Music size={14} />
            <span>Recorded Voice Memo</span>
          </div>
          {latestAudioMessage ? (
            <div className="voice-card-player" style={{ marginTop: "10px" }}>
              <audio controls src={latestAudioMessage.media_url} style={{ width: "100%", height: "24px" }} />
              <p className="voice-transcript-preview" style={{ fontSize: "0.75rem", marginTop: "6px", color: "var(--text-muted)" }}>
                Transcript: "{latestAudioMessage.text}"
              </p>
            </div>
          ) : (
            <div className="voice-empty-state">
              <span>No voice note attached to session.</span>
            </div>
          )}
          <span className="card-meta" style={{ marginTop: "8px", display: "block" }}>Sync active</span>
        </div>
      </section>
    </aside>
  );
}
