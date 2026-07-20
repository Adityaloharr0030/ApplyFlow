import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Global fetch interceptor to inject Auth token
const originalFetch = window.fetch;
window.fetch = async (url, options = {}) => {
  if (url.includes('/api/')) {
    const token = localStorage.getItem('token');
    if (token) {
      if (!options.headers) {
        options.headers = {};
      }
      if (options.headers instanceof Headers) {
        options.headers.append('Authorization', `Bearer ${token}`);
      } else {
        options.headers = {
          ...options.headers,
          'Authorization': `Bearer ${token}`
        };
      }
    }
  }
  
  const response = await originalFetch(url, options);
  
  // Optional: Auto-logout on 401
  if (response.status === 401) {
    localStorage.removeItem('token');
    if (!window.location.pathname.includes('/login')) {
      window.location.href = '/login';
    }
  }
  
  return response;
};
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
