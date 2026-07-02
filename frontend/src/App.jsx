import React, { useState, useEffect } from "react";
import SessionSidebar from "./components/SessionSidebar";
import ChatWindow from "./components/ChatWindow";
import Uploader from "./components/Uploader";
import RightPanel from "./components/RightPanel";
import Homepage from "./components/Homepage";
import { API_BASE_URL } from "./config";

export default function App() {
  const [view, setView] = useState("home");
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  
  // Modal / loading states
  const [uploaderOpen, setUploaderOpen] = useState(false);
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(false);

  // Mobile drawers states (only one open at a time)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [mobileRightPanelOpen, setMobileRightPanelOpen] = useState(false);

  const toggleMobileSidebar = () => {
    setMobileSidebarOpen((prev) => {
      const next = !prev;
      if (next) setMobileRightPanelOpen(false);
      return next;
    });
  };

  const toggleMobileRightPanel = () => {
    setMobileRightPanelOpen((prev) => {
      const next = !prev;
      if (next) setMobileSidebarOpen(false);
      return next;
    });
  };

  const closeAllDrawers = () => {
    setMobileSidebarOpen(false);
    setMobileRightPanelOpen(false);
  };

  // Prevent body scrolling when mobile drawers are visible
  useEffect(() => {
    if (mobileSidebarOpen || mobileRightPanelOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileSidebarOpen, mobileRightPanelOpen]);

  // 1. Fetch all active sessions on mount
  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    setLoadingSessions(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/sessions`);
      if (res.ok) {
        const data = await res.json();
        // Sort sessions by updated_at descending
        const sorted = data.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
        setSessions(sorted);
      }
    } catch (e) {
      console.error("Failed to load active sessions from backend:", e);
    } finally {
      setLoadingSessions(false);
    }
  };

  // 2. Select a session and retrieve message logs history
  const handleSelectSession = async (sessionId) => {
    setActiveSessionId(sessionId);
    closeAllDrawers();
    try {
      const res = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/messages`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch (e) {
      console.error(`Failed to load messages for session ${sessionId}:`, e);
    }
  };

  // 3. Create a new session instance
  const handleCreateSession = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/sessions`, { method: "POST" });
      if (res.ok) {
        const newSession = await res.json();
        setSessions((prev) => [newSession, ...prev]);
        setActiveSessionId(newSession.session_id);
        setMessages([]);
        closeAllDrawers();
      } else {
        alert(`Failed to create new session: Server returned status ${res.status}`);
      }
    } catch (e) {
      console.error("Failed to create new session:", e);
      alert(`Could not connect to backend at ${API_BASE_URL}. Please ensure the FastAPI server is running.`);
    }
  };

  // 4. Delete a session and clear screen history if active
  const handleDeleteSession = async (sessionId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}`, { method: "DELETE" });
      if (res.ok) {
        setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
        if (activeSessionId === sessionId) {
          setActiveSessionId(null);
          setMessages([]);
        }
      } else {
        alert(`Failed to delete session: Server returned status ${res.status}`);
      }
    } catch (e) {
      console.error(`Failed to delete session ${sessionId}:`, e);
      alert(`Could not connect to backend at ${API_BASE_URL} to delete session.`);
    }
  };

  // 5. Send plain text messages inside the active session
  const handleSendMessage = async (text) => {
    if (!activeSessionId) return;
    
    // Optimistic UI updates
    const userMsg = {
      sender: "user",
      text: text,
      type: "text",
      timestamp: new Date().toISOString(),
      metadata: null
    };
    setMessages((prev) => [...prev, userMsg]);
    setSending(true);

    try {
      const res = await fetch(`${API_BASE_URL}/api/chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: activeSessionId, text: text })
      });
      
      if (res.ok) {
        const reply = await res.json();
        setMessages((prev) => [...prev, reply]);
        // Refresh session list to update active UUIDs in sidebar
        await fetchSessions();
      } else {
        const errText = await res.text();
        throw new Error(errText);
      }
    } catch (e) {
      console.error("Message send failure:", e);
      const errorMsg = {
        sender: "assistant",
        text: `❌ Error sending message: ${e.message || "Server connection failed"}`,
        type: "text",
        timestamp: new Date().toISOString(),
        metadata: null
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setSending(false);
    }
  };

  // 6. Upload file media using Multipart Form Data
  const handleUploadFile = async (selectedFile) => {
    if (!activeSessionId) return;
    
    setUploading(true);
    setSending(true);
    setUploaderOpen(false);

    // Optimistic UI updates for file attachment
    const classType = selectedFile.type.startsWith("image/") ? "image" : "audio";
    const attachmentMsg = {
      sender: "user",
      text: classType === "image" ? "Uploaded business card image." : "Uploaded voice note audio.",
      type: classType,
      timestamp: new Date().toISOString(),
      metadata: { mime: selectedFile.type }
    };
    setMessages((prev) => [...prev, attachmentMsg]);

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("session_id", activeSessionId);

    try {
      const res = await fetch(`${API_BASE_URL}/api/chat/upload`, {
        method: "POST",
        body: formData
      });
      
      if (res.ok) {
        const reply = await res.json();
        setMessages((prev) => [...prev, reply]);
        // Refresh session list to update active UUIDs in sidebar
        await fetchSessions();
      } else {
        const errText = await res.text();
        throw new Error(errText);
      }
    } catch (e) {
      console.error("Media upload failure:", e);
      const errorMsg = {
        sender: "assistant",
        text: `❌ Media processing failed: ${e.message || "Server upload failed"}`,
        type: "text",
        timestamp: new Date().toISOString(),
        metadata: null
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setUploading(false);
      setSending(false);
    }
  };

  // Scan message logs history dynamically to resolve the active contact metadata
  const activeContact = [...messages].reverse().find(msg => msg.metadata?.extracted_contact)?.metadata?.extracted_contact;

  if (view === "home") {
    return <Homepage onLaunchApp={() => setView("app")} />;
  }

  return (
    <>
      {/* Background ambient animation blobs */}
      <div className="bg-blobs">
        <div className="blob blob-1" />
        <div className="blob blob-2" />
        <div className="blob blob-3" />
      </div>

      {/* Semi-transparent overlay behind active drawers */}
      {(mobileSidebarOpen || mobileRightPanelOpen) && (
        <div className="drawer-overlay" onClick={closeAllDrawers} />
      )}

      <div className={`app-container ${activeContact ? "has-right-panel" : "no-right-panel"} ${mobileSidebarOpen ? "sidebar-open" : ""} ${mobileRightPanelOpen ? "right-panel-open" : ""}`}>
        {/* Sessions sidebar */}
        <SessionSidebar 
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={handleSelectSession}
          onCreateSession={handleCreateSession}
          onDeleteSession={handleDeleteSession}
          loadingSessions={loadingSessions}
          onBackToHome={() => setView("home")}
        />

        {/* Main chat window workspace */}
        <ChatWindow 
          messages={messages}
          onSendMessage={handleSendMessage}
          onOpenUploader={() => setUploaderOpen(true)}
          onUploadFile={handleUploadFile}
          onBackToHome={() => setView("home")}
          sending={sending}
          activeSessionId={activeSessionId}
          onToggleSidebar={toggleMobileSidebar}
          onToggleRightPanel={toggleMobileRightPanel}
          hasActiveContact={!!activeContact}
          mobileSidebarOpen={mobileSidebarOpen}
          mobileRightPanelOpen={mobileRightPanelOpen}
        />

        {/* Right side contact profile panel */}
        {activeContact && (
          <RightPanel 
            activeContact={activeContact}
            messages={messages}
          />
        )}

        {/* Drag & drop file upload modal */}
        {uploaderOpen && (
          <Uploader 
            onClose={() => setUploaderOpen(false)}
            onUpload={handleUploadFile}
            uploading={uploading}
          />
        )}
      </div>
    </>
  );
}
