import React, { useState, useEffect, useRef } from "react";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export default function Builder() {
  const [spec, setSpec] = useState("");
  const [name, setName] = useState("MyApp");
  const [projectId, setProjectId] = useState(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState("");
  const [error, setError] = useState("");
  const pollingRef = useRef(null);

  // Auto-poll status when project is being generated
  useEffect(() => {
    if (projectId && !["ready", "failed"].includes(status)) {
      pollingRef.current = setInterval(async () => {
        try {
          const res = await axios.get(`${API_BASE}/projects/${projectId}`);
          const project = res.data;
          setStatus(project.status);
          if (project.status === "ready") {
            setDownloadUrl(`${API_BASE}/projects/${projectId}/download`);
            clearInterval(pollingRef.current);
          } else if (project.status === "failed") {
            setError("Generation failed. Please try again.");
            clearInterval(pollingRef.current);
          }
        } catch (err) {
          setError(err.response?.data?.detail || err.message);
          clearInterval(pollingRef.current);
        }
      }, 1500);
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [projectId, status]);

  async function submit() {
    if (!name.trim() || !spec.trim()) {
      setError("Name and specification are required");
      return;
    }
    setLoading(true);
    setStatus("creating");
    setError("");
    setDownloadUrl("");
    setProjectId(null);
    
    try {
      const res = await axios.post(`${API_BASE}/projects/`, { name, spec });
      setProjectId(res.data.id);
      setStatus(res.data.status || "pending");
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      setStatus("");
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setSpec("");
    setName("MyApp");
    setProjectId(null);
    setStatus("");
    setDownloadUrl("");
    setError("");
    if (pollingRef.current) clearInterval(pollingRef.current);
  }

  const statusColor = {
    pending: "text-yellow-600",
    generating: "text-blue-600",
    ready: "text-green-600",
    failed: "text-red-600",
    creating: "text-gray-600",
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-3xl mx-auto px-4">
        <div className="bg-white rounded-lg shadow-md p-6">
          <h1 className="text-2xl font-bold text-gray-800 mb-6">🚀 AI App Builder</h1>
          
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
              {error}
            </div>
          )}

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Project Name
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={loading}
              className="border border-gray-300 p-2.5 w-full rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
              placeholder="Enter project name"
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              App Specification
            </label>
            <textarea
              value={spec}
              onChange={(e) => setSpec(e.target.value)}
              disabled={loading}
              rows={10}
              className="border border-gray-300 w-full p-2.5 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 resize-none"
              placeholder="Describe your app in detail...&#10;&#10;Example:&#10;A todo list app with:&#10;- User authentication&#10;- Create, edit, delete tasks&#10;- Mark tasks as complete&#10;- Filter by status"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={submit}
              disabled={loading || !name.trim() || !spec.trim()}
              className={`px-5 py-2.5 rounded-md text-white font-medium transition-colors ${
                loading || !name.trim() || !spec.trim()
                  ? "bg-gray-400 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700"
              }`}
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Generating...
                </span>
              ) : (
                "Generate App"
              )}
            </button>
            
            {projectId && (
              <button
                onClick={reset}
                className="px-4 py-2.5 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
              >
                New Project
              </button>
            )}
          </div>

          {/* Status Section */}
          {(status || projectId) && (
            <div className="mt-6 p-4 bg-gray-50 rounded-md border">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm text-gray-500">Status: </span>
                  <span className={`font-medium ${statusColor[status] || "text-gray-800"}`}>
                    {status === "generating" && "⏳ "}
                    {status === "ready" && "✅ "}
                    {status === "failed" && "❌ "}
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </span>
                </div>
                {projectId && (
                  <span className="text-sm text-gray-500">
                    Project #{projectId}
                  </span>
                )}
              </div>
              
              {downloadUrl && (
                <div className="mt-4">
                  <a
                    href={downloadUrl}
                    download
                    className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Download ZIP
                  </a>
                </div>
              )}
            </div>
          )}
        </div>

        <p className="text-center text-sm text-gray-500 mt-6">
          Powered by AI • FastAPI + React
        </p>
      </div>
    </div>
  );
}
