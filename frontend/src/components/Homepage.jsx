import React from "react";
import { FolderSync, Sparkles, FileSpreadsheet, Mic, MessageSquare, ArrowRight, CheckCircle2 } from "lucide-react";

export default function Homepage({ onLaunchApp }) {
  return (
    <div className="homepage-container">
      {/* 1. Header Navbar */}
      <header className="home-header">
        <div className="home-logo">
          <FolderSync size={24} style={{ color: "var(--accent-primary)" }} />
          <span className="font-display">Krid Orchestrator</span>
        </div>
        <nav className="home-nav">
          <a href="#features" className="nav-link">Features</a>
          <a href="#how-it-works" className="nav-link">Workflow</a>
          <button className="nav-cta-btn font-display" onClick={onLaunchApp}>
            Launch App
          </button>
        </nav>
      </header>

      {/* 2. Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <div className="hero-badge">
            <Sparkles size={14} />
            <span>AI-Powered Contact Assistant</span>
          </div>
          <h1 className="font-display hero-title">
            Digitize Business Cards & Voice Notes <span className="highlight-text">Instantly</span>
          </h1>
          <p className="hero-subtitle">
            Upload contact cards, record browser-native voice notes, sync profiles to Google Sheets, and trigger automated WhatsApp alerts in one unified workspace.
          </p>
          <div className="hero-actions">
            <button className="primary-cta font-display" onClick={onLaunchApp}>
              Get Started Free <ArrowRight size={16} />
            </button>
            <a href="#features" className="secondary-cta font-display">
              Learn More
            </a>
          </div>
        </div>
        
        <div className="hero-illustration">
          <div className="illustration-card-mockup">
            <div className="mockup-header">
              <div className="dot red" />
              <div className="dot yellow" />
              <div className="dot green" />
            </div>
            <div className="mockup-body">
              <div className="mockup-sidebar">
                <div className="sidebar-line active" />
                <div className="sidebar-line" />
                <div className="sidebar-line" />
              </div>
              <div className="mockup-chat">
                <div className="bubble user">Uploaded card image</div>
                <div className="bubble assistant card-parsed">
                  <strong>✓ Card Parsed Successfully</strong>
                  <span>Name: John Smith</span>
                  <span>Company: Acme Corp</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Features Section */}
      <section id="features" className="features-section">
        <h2 className="font-display section-title-center">What Krid Orchestrator Does</h2>
        <p className="section-subtitle-center">
          Streamline contact retrieval and digitization with state-of-the-art AI intelligence.
        </p>

        <div className="features-grid-home">
          <div className="home-feature-card lavender-card-home">
            <div className="card-icon-wrapper">
              <Sparkles size={24} />
            </div>
            <h3 className="font-display card-title-home">AI Business Card OCR</h3>
            <p className="card-desc-home">
              Upload business cards to instantly extract names, phone numbers, emails, and company metadata using Gemini Flash.
            </p>
          </div>

          <div className="home-feature-card mint-card-home">
            <div className="card-icon-wrapper">
              <FileSpreadsheet size={24} />
            </div>
            <h3 className="font-display card-title-home">Google Sheets Sync</h3>
            <p className="card-desc-home">
              Store contact profiles in organized Google Sheet rows automatically. Features built-in duplicate matching rules.
            </p>
          </div>

          <div className="home-feature-card peach-card-home">
            <div className="card-icon-wrapper">
              <Mic size={24} />
            </div>
            <h3 className="font-display card-title-home">Voice Note Transcripts</h3>
            <p className="card-desc-home">
              Record browser voice notes or upload audio files. Transcripts append to Google Sheets and link to MongoDB sessions.
            </p>
          </div>

          <div className="home-feature-card blue-card-home">
            <div className="card-icon-wrapper">
              <MessageSquare size={24} />
            </div>
            <h3 className="font-display card-title-home">WhatsApp Dispatch</h3>
            <p className="card-desc-home">
              Trigger automated WhatsApp Meta Cloud alerts to notify team managers whenever a new client contact is registered.
            </p>
          </div>
        </div>
      </section>

      {/* 4. Workflow Section */}
      <section id="how-it-works" className="workflow-section">
        <h2 className="font-display section-title-center">Seamless Integration Flow</h2>
        <p className="section-subtitle-center">
          How our agent coordinates multiple microservices to organize your contacts.
        </p>

        <div className="steps-container">
          <div className="step-item">
            <div className="step-number">1</div>
            <h4 className="font-display step-title">Upload & Scan</h4>
            <p className="step-desc">Upload a card image. Gemini extracts and validates structured contact data.</p>
          </div>
          <div className="step-item">
            <div className="step-number">2</div>
            <h4 className="font-display step-title">Verify & Sync</h4>
            <p className="step-desc">Checks for duplicate entries in Google Sheets and links the session UUID in MongoDB.</p>
          </div>
          <div className="step-item">
            <div className="step-number">3</div>
            <h4 className="font-display step-title">Alert & Append</h4>
            <p className="step-desc">Meta WhatsApp fires notification warnings, and audio notes attach logs to the contact.</p>
          </div>
        </div>
      </section>

      {/* 5. CTA Footer Section */}
      <section className="cta-footer-section">
        <h2 className="font-display cta-title">Ready to Digitize Your Contacts?</h2>
        <p className="cta-desc">Launch the secure workspace dashboard and start managing card data instantly.</p>
        <button className="primary-cta font-display large-cta" onClick={onLaunchApp}>
          Launch App Workspace
        </button>
      </section>

      <footer className="footer-home">
        <p>&copy; {new Date().getFullYear()} Krid Orchestrator. All rights reserved.</p>
      </footer>
    </div>
  );
}
