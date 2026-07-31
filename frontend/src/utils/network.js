import { API_BASE } from "../api.js";

export const checkHealth = async () => {
  try {
    const response = await fetch(`${API_BASE}/health`, { 
      cache: "no-store",
      signal: AbortSignal.timeout(10000) // 10 second timeout
    });
    return response.ok;
  } catch {
    return false;
  }
};

export const isOnline = () => {
  return navigator.onLine;
};

export const addNetworkListener = (callback) => {
  window.addEventListener('online', callback);
  window.addEventListener('offline', callback);
  return () => {
    window.removeEventListener('online', callback);
    window.removeEventListener('offline', callback);
  };
};
