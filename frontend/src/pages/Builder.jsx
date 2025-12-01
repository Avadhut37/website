import React, { useState, useEffect, useRef } from "react";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

// Simple syntax highlighting for code
function highlightCode(code, language) {
  if (!code) return "";
  
  let highlighted = code
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  if (language === "python") {
    highlighted = highlighted.replace(
      /\b(def|class|import|from|return|if|else|elif|for|while|try|except|with|as|async|await|True|False|None|and|or|not|in|is)\b/g,
      '<span class="text-purple-400 font-semibold">$1</span>'
    );
    highlighted = highlighted.replace(
      /(["'`])(?:(?!\1)[^\\]|\\.)*?\1/g,
      '<span class="text-green-400">$&</span>'
    );
    highlighted = highlighted.replace(
      /(#.*$)/gm,
      '<span class="text-gray-500 italic">$1</span>'
    );
    highlighted = highlighted.replace(
      /(@\w+)/g,
      '<span class="text-yellow-400">$1</span>'
    );
  } else if (language === "javascript" || language === "jsx") {
    highlighted = highlighted.replace(
      /\b(const|let|var|function|return|if|else|for|while|class|import|export|from|default|async|await|try|catch|new|this|true|false|null|undefined)\b/g,
      '<span class="text-purple-400 font-semibold">$1</span>'
    );
    highlighted = highlighted.replace(
      /(["'`])(?:(?!\1)[^\\]|\\.)*?\1/g,
      '<span class="text-green-400">$&</span>'
    );
    highlighted = highlighted.replace(
      /(\/\/.*$)/gm,
      '<span class="text-gray-500 italic">$1</span>'
    );
  } else if (language === "html") {
    highlighted = highlighted.replace(
      /(&lt;\/?[a-z]\w*)/gi,
      '<span class="text-blue-400">$1</span>'
    );
  }

  return highlighted;
}

// File tree component
function FileTree({ files, selectedFile, onSelect }) {
  const fileList = Object.keys(files).sort((a, b) => {
    const aIsFolder = a.includes("/");
    const bIsFolder = b.includes("/");
    if (aIsFolder && !bIsFolder) return -1;
    if (!aIsFolder && bIsFolder) return 1;
    return a.localeCompare(b);
  });

  const getFileIcon = (filename) => {
    if (filename.endsWith(".py")) return "🐍";
    if (filename.endsWith(".js") || filename.endsWith(".jsx")) return "📜";
    if (filename.endsWith(".html")) return "🌐";
    if (filename.endsWith(".css")) return "🎨";
    if (filename.endsWith(".json")) return "📋";
    if (filename.endsWith(".txt") || filename.endsWith(".md")) return "📄";
    return "📄";
  };

  return (
    <div className="bg-gray-900 text-gray-300 p-2 overflow-y-auto h-full">
      <div className="text-xs font-semibold text-gray-500 uppercase mb-2 px-2">Files</div>
      {fileList.map((filename) => (
        <div
          key={filename}
          onClick={() => onSelect(filename)}
          className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer text-sm truncate ${
            selectedFile === filename
              ? "bg-blue-600 text-white"
              : "hover:bg-gray-800"
          }`}
        >
          <span>{getFileIcon(filename)}</span>
          <span className="truncate">{filename}</span>
        </div>
      ))}
    </div>
  );
}

// Code editor component
function CodeEditor({ code, language, filename }) {
  const lines = code ? code.split("\n") : [];
  
  return (
    <div className="h-full flex flex-col bg-gray-900">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <span className="text-gray-300 text-sm font-medium">{filename || "Select a file"}</span>
        <button
          onClick={() => navigator.clipboard.writeText(code)}
          className="text-xs px-2 py-1 bg-gray-700 text-gray-300 rounded hover:bg-gray-600"
        >
          📋 Copy
        </button>
      </div>
      
      <div className="flex-1 overflow-auto font-mono text-sm">
        {code ? (
          <div className="flex min-h-full">
            <div className="bg-gray-800 text-gray-500 text-right py-4 px-2 select-none sticky left-0">
              {lines.map((_, i) => (
                <div key={i} className="leading-6">{i + 1}</div>
              ))}
            </div>
            <pre className="flex-1 py-4 px-4 text-gray-300 overflow-x-auto">
              <code
                dangerouslySetInnerHTML={{
                  __html: highlightCode(code, language),
                }}
                className="leading-6 block"
              />
            </pre>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            Select a file to view code
          </div>
        )}
      </div>
    </div>
  );
}

// Live preview component
function LivePreview({ files, appName }) {
  const [previewHtml, setPreviewHtml] = useState("");

  useEffect(() => {
    if (!files) return;

    const htmlFile = Object.keys(files).find(
      (f) => f.endsWith("index.html") || f.endsWith(".html")
    );
    
    if (htmlFile && files[htmlFile]) {
      let html = files[htmlFile];
      
      const cssFile = Object.keys(files).find((f) => f.endsWith(".css"));
      if (cssFile && files[cssFile]) {
        html = html.replace("</head>", `<style>${files[cssFile]}</style></head>`);
      }

      const jsFile = Object.keys(files).find(
        (f) => f.endsWith(".js") && !f.includes("config")
      );
      if (jsFile && files[jsFile]) {
        html = html.replace("</body>", `<script>${files[jsFile]}</script></body>`);
      }

      setPreviewHtml(html);
    } else {
      // Generate preview card for backend-only apps
      setPreviewHtml(`
        <!DOCTYPE html>
        <html>
        <head>
          <title>${appName} - Preview</title>
          <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
              min-height: 100vh;
              display: flex;
              align-items: center;
              justify-content: center;
              padding: 20px;
            }
            .container {
              background: white;
              border-radius: 16px;
              padding: 40px;
              max-width: 500px;
              width: 100%;
              box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            h1 { color: #1a1a2e; margin-bottom: 10px; font-size: 24px; }
            .badge { 
              display: inline-block;
              background: #10b981;
              color: white;
              padding: 4px 12px;
              border-radius: 20px;
              font-size: 12px;
              margin-bottom: 20px;
            }
            p { color: #666; line-height: 1.6; margin-bottom: 16px; font-size: 14px; }
            .api-box {
              background: #f8f9fa;
              border-radius: 8px;
              padding: 16px;
              margin: 16px 0;
            }
            .api-box h3 { font-size: 13px; color: #333; margin-bottom: 10px; }
            .endpoint {
              background: #1a1a2e;
              color: #10b981;
              padding: 6px 10px;
              border-radius: 6px;
              font-family: monospace;
              font-size: 12px;
              margin: 4px 0;
            }
            .method { color: #f59e0b; font-weight: bold; margin-right: 8px; }
            .tech-stack { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 16px; }
            .tech {
              background: #e0e7ff;
              color: #4338ca;
              padding: 4px 10px;
              border-radius: 6px;
              font-size: 11px;
              font-weight: 500;
            }
          </style>
        </head>
        <body>
          <div class="container">
            <span class="badge">✨ Generated by AI</span>
            <h1>🚀 ${appName}</h1>
            <p>Your FastAPI backend is ready with models, routes, and API endpoints.</p>
            <div class="api-box">
              <h3>📡 API Endpoints</h3>
              <div class="endpoint"><span class="method">GET</span>/api/items</div>
              <div class="endpoint"><span class="method">POST</span>/api/items</div>
              <div class="endpoint"><span class="method">GET</span>/api/items/{id}</div>
              <div class="endpoint"><span class="method">DELETE</span>/api/items/{id}</div>
            </div>
            <div class="tech-stack">
              <span class="tech">🐍 Python</span>
              <span class="tech">⚡ FastAPI</span>
              <span class="tech">🗄️ SQLModel</span>
            </div>
          </div>
        </body>
        </html>
      `);
    }
  }, [files, appName]);

  return (
    <div className="h-full flex flex-col bg-white">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-100 border-b">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
          </div>
          <span className="text-gray-600 text-sm ml-2">Preview</span>
        </div>
        <button
          onClick={() => {
            const win = window.open("", "_blank");
            win.document.write(previewHtml);
          }}
          className="text-xs px-2 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
        >
          🔗 Open in tab
        </button>
      </div>
      
      <div className="flex-1 bg-gray-200">
        {previewHtml ? (
          <iframe
            srcDoc={previewHtml}
            className="w-full h-full border-0"
            title="App Preview"
            sandbox="allow-scripts"
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <div className="text-4xl mb-2">🎨</div>
              <p>Preview will appear here</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Builder() {
  const [spec, setSpec] = useState("");
  const [name, setName] = useState("MyApp");
  const [projectId, setProjectId] = useState(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [files, setFiles] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [showPreview, setShowPreview] = useState(false);
  const [activeTab, setActiveTab] = useState("code");
  const pollingRef = useRef(null);

  const getLanguage = (filename) => {
    if (!filename) return "text";
    if (filename.endsWith(".py")) return "python";
    if (filename.endsWith(".js") || filename.endsWith(".jsx")) return "javascript";
    if (filename.endsWith(".html")) return "html";
    if (filename.endsWith(".css")) return "css";
    return "text";
  };

  useEffect(() => {
    if (projectId && !["ready", "failed"].includes(status)) {
      pollingRef.current = setInterval(async () => {
        try {
          const res = await axios.get(`${API_BASE}/projects/${projectId}`);
          setStatus(res.data.status);
          
          if (res.data.status === "ready") {
            try {
              const filesRes = await axios.get(`${API_BASE}/projects/${projectId}/files`);
              setFiles(filesRes.data.files || filesRes.data);
              const fileKeys = Object.keys(filesRes.data.files || filesRes.data);
              if (fileKeys.length > 0) {
                setSelectedFile(fileKeys.find(f => f.includes("main.py")) || fileKeys[0]);
              }
            } catch (e) {
              console.error("Failed to fetch files:", e);
            }
            clearInterval(pollingRef.current);
          } else if (res.data.status === "failed") {
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
    setStatus("generating");
    setError("");
    setFiles(null);
    setSelectedFile(null);
    setShowPreview(true);

    try {
      const res = await axios.post(`${API_BASE}/ai/preview`, {
        spec: { raw: spec, name: name }
      });
      
      if (res.data.files) {
        setFiles(res.data.files);
        setStatus("ready");
        const fileKeys = Object.keys(res.data.files);
        const mainFile = fileKeys.find(f => f.includes("main.py")) || 
                        fileKeys.find(f => f.includes("index.html")) ||
                        fileKeys[0];
        if (mainFile) setSelectedFile(mainFile);
      }
    } catch (err) {
      try {
        const res = await axios.post(`${API_BASE}/projects/`, { name, spec });
        setProjectId(res.data.id);
        setStatus(res.data.status || "pending");
      } catch (e) {
        setError(e.response?.data?.detail || e.message);
        setStatus("");
        setShowPreview(false);
      }
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setSpec("");
    setName("MyApp");
    setProjectId(null);
    setStatus("");
    setError("");
    setFiles(null);
    setSelectedFile(null);
    setShowPreview(false);
    if (pollingRef.current) clearInterval(pollingRef.current);
  }

  async function downloadZip() {
    if (!files) return;
    
    // Create a simple download by generating content
    const content = Object.entries(files)
      .map(([name, code]) => `// ===== ${name} =====\n${code}`)
      .join("\n\n");
    
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${name}-source.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const statusColor = {
    pending: "text-yellow-500",
    generating: "text-blue-500",
    ready: "text-green-500",
    failed: "text-red-500",
  };

  // Input form view
  if (!showPreview) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 py-8">
        <div className="max-w-3xl mx-auto px-4">
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-8 border border-white/20">
            <div className="flex items-center gap-3 mb-8">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center text-2xl">
                🚀
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">AI App Builder</h1>
                <p className="text-gray-400 text-sm">Generate full-stack apps with AI</p>
              </div>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-red-500/20 border border-red-500/50 rounded-xl text-red-200 text-sm">
                {error}
              </div>
            )}

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Project Name
              </label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={loading}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
                placeholder="Enter project name"
              />
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                App Specification
              </label>
              <textarea
                value={spec}
                onChange={(e) => setSpec(e.target.value)}
                disabled={loading}
                rows={8}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50 resize-none"
                placeholder={`Describe your app in detail...

Example:
An e-commerce store with:
- Product catalog with categories
- Shopping cart functionality
- User authentication
- Order management`}
              />
            </div>

            <button
              onClick={submit}
              disabled={loading || !name.trim() || !spec.trim()}
              className={`w-full py-4 rounded-xl text-white font-semibold text-lg transition-all transform hover:scale-[1.02] ${
                loading || !name.trim() || !spec.trim()
                  ? "bg-gray-600 cursor-not-allowed"
                  : "bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 shadow-lg hover:shadow-purple-500/25"
              }`}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-3">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Generating...
                </span>
              ) : (
                "✨ Generate App"
              )}
            </button>

            <div className="mt-8 grid grid-cols-4 gap-4 text-center">
              {[
                { icon: "⚡", label: "Fast", desc: "< 30 sec" },
                { icon: "🎯", label: "Smart", desc: "AI-powered" },
                { icon: "📦", label: "Complete", desc: "Full-stack" },
                { icon: "🆓", label: "Free", desc: "No limits" },
              ].map((item) => (
                <div key={item.label} className="p-3 bg-white/5 rounded-xl">
                  <div className="text-2xl mb-1">{item.icon}</div>
                  <div className="text-white font-medium text-sm">{item.label}</div>
                  <div className="text-gray-500 text-xs">{item.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Split view with code and preview
  return (
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-4">
          <button
            onClick={reset}
            className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 text-sm"
          >
            ← Back
          </button>
          <div className="flex items-center gap-2">
            <span className="text-white font-semibold">{name}</span>
            <span className={`text-sm ${statusColor[status] || "text-gray-400"}`}>
              {status === "generating" && "⏳ Generating..."}
              {status === "ready" && "✅ Ready"}
              {status === "failed" && "❌ Failed"}
              {status === "pending" && "⏳ Pending..."}
            </span>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <div className="flex bg-gray-700 rounded-lg p-1 md:hidden">
            <button
              onClick={() => setActiveTab("code")}
              className={`px-3 py-1 rounded text-sm ${
                activeTab === "code" ? "bg-gray-600 text-white" : "text-gray-400"
              }`}
            >
              Code
            </button>
            <button
              onClick={() => setActiveTab("preview")}
              className={`px-3 py-1 rounded text-sm ${
                activeTab === "preview" ? "bg-gray-600 text-white" : "text-gray-400"
              }`}
            >
              Preview
            </button>
          </div>
          
          {files && (
            <button
              onClick={downloadZip}
              className="flex items-center gap-2 px-4 py-1.5 bg-green-600 text-white rounded-lg hover:bg-green-500 text-sm"
            >
              📥 Download
            </button>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* File tree */}
        {files && (
          <div className="w-48 border-r border-gray-700 hidden md:block">
            <FileTree
              files={files}
              selectedFile={selectedFile}
              onSelect={setSelectedFile}
            />
          </div>
        )}

        {/* Code editor */}
        <div className={`flex-1 ${activeTab === "preview" ? "hidden md:block" : ""}`}>
          {loading ? (
            <div className="h-full flex items-center justify-center bg-gray-900">
              <div className="text-center">
                <div className="animate-spin w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full mx-auto mb-4"></div>
                <p className="text-gray-400">Generating code...</p>
                <p className="text-gray-500 text-sm mt-2">This may take a few seconds</p>
              </div>
            </div>
          ) : (
            <CodeEditor
              code={files && selectedFile ? files[selectedFile] : ""}
              language={getLanguage(selectedFile)}
              filename={selectedFile}
            />
          )}
        </div>

        {/* Preview panel */}
        <div className={`w-full md:w-1/2 border-l border-gray-700 ${activeTab === "code" ? "hidden md:block" : ""}`}>
          <LivePreview files={files} appName={name} />
        </div>
      </div>

      {/* Mobile file selector */}
      {files && (
        <div className="md:hidden border-t border-gray-700 bg-gray-800 p-2">
          <select
            value={selectedFile || ""}
            onChange={(e) => setSelectedFile(e.target.value)}
            className="w-full bg-gray-700 text-white rounded px-3 py-2 text-sm"
          >
            {Object.keys(files).map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}
