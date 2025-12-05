import React, { useState, useEffect } from 'react';
import { apiClient, API_BASE_URL, API_V1 } from '../config/api';

export default function ConnectionStatus() {
  const [status, setStatus] = useState('checking');
  const [info, setInfo] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    checkConnection();
  }, []);

  const checkConnection = async () => {
    setStatus('checking');
    setError(null);
    
    try {
      console.log('🔍 Testing connection to:', API_BASE_URL);
      const response = await fetch(`${API_BASE_URL}/health`, {
        method: 'GET',
        mode: 'cors',
        cache: 'no-cache',
        headers: {
          'Accept': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.status === 'ok') {
        setStatus('connected');
        setInfo(data);
        console.log('✅ Backend connection successful:', data);
      } else {
        throw new Error('Backend returned non-ok status');
      }
    } catch (err) {
      setStatus('error');
      setError(err.message);
      console.error('❌ Backend connection failed:', err);
      console.error('💡 If using Codespaces, make sure port 8000 is set to PUBLIC visibility in the PORTS tab');
    }
  };

  if (status === 'checking') {
    return (
      <div className="fixed bottom-4 right-4 bg-blue-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2">
        <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
        <span>Checking backend connection...</span>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="fixed bottom-4 right-4 bg-red-500 text-white px-4 py-3 rounded-lg shadow-lg max-w-md z-50">
        <div className="flex items-start gap-2">
          <span className="text-xl">❌</span>
          <div className="flex-1">
            <div className="font-bold">Backend Connection Failed</div>
            <div className="text-sm mt-1 opacity-90">
              Cannot connect to {API_BASE_URL}
            </div>
            {error && (
              <div className="text-xs mt-1 opacity-75 font-mono bg-red-600 p-2 rounded mt-2">
                {error}
              </div>
            )}
            <div className="mt-2 text-xs bg-red-600 p-2 rounded">
              <strong>Codespaces Fix:</strong><br/>
              1. Click <strong>PORTS</strong> tab (bottom panel)<br/>
              2. Find port <strong>8000</strong><br/>
              3. Right-click → <strong>Port Visibility</strong> → <strong>Public</strong>
            </div>
            <button
              onClick={checkConnection}
              className="mt-2 text-xs bg-white text-red-500 px-3 py-1 rounded hover:bg-red-50 transition"
            >
              Retry Connection
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 group cursor-pointer">
      <span className="text-xl">✅</span>
      <div>
        <div className="font-semibold">Backend Connected</div>
        <div className="text-xs opacity-90">{info?.version}</div>
      </div>
      
      {/* Hover details */}
      <div className="hidden group-hover:block absolute bottom-full right-0 mb-2 bg-gray-900 text-white text-xs rounded-lg p-3 shadow-xl w-80">
        <div className="font-bold mb-2">Connection Details</div>
        <div className="space-y-1 font-mono">
          <div>
            <span className="text-gray-400">Backend URL:</span>
            <div className="text-green-400 break-all">{API_BASE_URL}</div>
          </div>
          <div>
            <span className="text-gray-400">API Endpoint:</span>
            <div className="text-green-400 break-all">{API_V1}</div>
          </div>
          <div>
            <span className="text-gray-400">Environment:</span>
            <div className="text-green-400">{info?.environment || 'unknown'}</div>
          </div>
          {info?.codespace && (
            <div className="mt-2 pt-2 border-t border-gray-700">
              <div className="text-gray-400">GitHub Codespace:</div>
              <div className="text-blue-400">{info.codespace.name}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
