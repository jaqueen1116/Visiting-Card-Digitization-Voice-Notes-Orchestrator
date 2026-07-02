// Configuration file for frontend API calls
const isLocal = 
  window.location.hostname === "localhost" || 
  window.location.hostname === "127.0.0.1" || 
  /^\d+\.\d+\.\d+\.\d+$/.test(window.location.hostname) ||
  window.location.hostname.endsWith(".local");

export const API_BASE_URL = isLocal
  ? `${window.location.protocol}//${window.location.hostname}:8001`
  : (import.meta.env.VITE_API_URL || "http://127.0.0.1:8001");
