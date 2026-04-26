import axios from 'axios';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Simple Event Emitter for API logs
export const apiEvents = new EventTarget();

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  // Log request
  apiEvents.dispatchEvent(new CustomEvent('request', { 
    detail: { 
      method: config.method.toUpperCase(), 
      url: config.url,
      timestamp: new Date().toLocaleTimeString()
    } 
  }));
  
  return config;
});

client.interceptors.response.use(
  (response) => {
    apiEvents.dispatchEvent(new CustomEvent('response', { 
      detail: { 
        method: response.config.method.toUpperCase(), 
        url: response.config.url,
        status: response.status,
        timestamp: new Date().toLocaleTimeString()
      } 
    }));
    return response;
  },
  (error) => {
    apiEvents.dispatchEvent(new CustomEvent('response', { 
      detail: { 
        method: error.config?.method?.toUpperCase() || 'GET', 
        url: error.config?.url || 'Unknown',
        status: error.response?.status || 'FAIL',
        timestamp: new Date().toLocaleTimeString()
      } 
    }));
    return Promise.reject(error);
  }
);

export default client;
