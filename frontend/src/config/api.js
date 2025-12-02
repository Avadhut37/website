/**
 * API Configuration for GitHub Codespaces and Local Development
 * Automatically detects environment and uses correct backend URL
 */

/**
 * Get the backend API URL based on environment
 * - GitHub Codespaces: Uses forwarded port URL
 * - Local: Uses localhost:8000
 */
function getApiUrl() {
  // Check if we're in GitHub Codespaces
  const isCodespaces = window.location.hostname.includes('github.dev') || 
                       window.location.hostname.includes('githubpreview.dev') ||
                       window.location.hostname.includes('app.github.dev');
  
  if (isCodespaces) {
    // In Codespaces, backend runs on same domain but port 8000
    // Extract the base URL and modify it for port 8000
    const currentUrl = window.location.origin;
    
    // GitHub Codespaces URL format: https://something-8000.app.github.dev
    // We need to replace the port in the URL (handling dynamic ports like 5173, 5174, 5175)
    const baseUrl = currentUrl.replace(/-(\d+)(\.app\.github\.dev|\.preview\.app\.github\.dev|\.github\.dev)/, '-8000$2');
    
    console.log('🌐 Codespaces detected - API URL:', baseUrl);
    return baseUrl;
  }
  
  // Local development or custom VITE_API_URL
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  console.log('🏠 Local development - API URL:', apiUrl);
  return apiUrl;
}

// Export the API base URL
export const API_BASE_URL = getApiUrl();
export const API_V1 = `${API_BASE_URL}/api/v1`;

// Export axios instance with proper configuration
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: API_V1,
  timeout: 180000, // 3 minutes for AI generation
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for debugging
apiClient.interceptors.request.use(
  (config) => {
    console.log('📤 API Request:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('📤 Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for debugging
apiClient.interceptors.response.use(
  (response) => {
    console.log('📥 API Response:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('📥 Response Error:', error.response?.status, error.message);
    if (error.response) {
      console.error('Error details:', error.response.data);
    }
    return Promise.reject(error);
  }
);

export default apiClient;
