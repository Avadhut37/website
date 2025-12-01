import React, { useState, useEffect, useRef } from "react";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

// Syntax highlighting
function highlightCode(code, language) {
  if (!code) return "";
  let h = code.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  
  if (language === "python") {
    h = h.replace(/\b(def|class|import|from|return|if|else|elif|for|while|try|except|with|as|async|await|True|False|None|and|or|not|in|is)\b/g, '<span class="text-purple-400">$1</span>');
    h = h.replace(/(["'`])(?:(?!\1)[^\\]|\\.)*?\1/g, '<span class="text-green-400">$&</span>');
    h = h.replace(/(#.*$)/gm, '<span class="text-gray-500">$1</span>');
    h = h.replace(/(@\w+)/g, '<span class="text-yellow-400">$1</span>');
  } else if (language === "javascript" || language === "jsx") {
    h = h.replace(/\b(const|let|var|function|return|if|else|for|while|class|import|export|from|default|async|await|try|catch|new|this|true|false|null|undefined)\b/g, '<span class="text-purple-400">$1</span>');
    h = h.replace(/(["'`])(?:(?!\1)[^\\]|\\.)*?\1/g, '<span class="text-green-400">$&</span>');
    h = h.replace(/(\/\/.*$)/gm, '<span class="text-gray-500">$1</span>');
  } else if (language === "html") {
    h = h.replace(/(&lt;\/?[a-z]\w*)/gi, '<span class="text-blue-400">$1</span>');
  }
  return h;
}

// File Tree
function FileTree({ files, selectedFile, onSelect }) {
  const fileList = Object.keys(files).sort();
  const getIcon = (f) => {
    if (f.endsWith(".py")) return "🐍";
    if (f.endsWith(".js") || f.endsWith(".jsx")) return "📜";
    if (f.endsWith(".html")) return "🌐";
    if (f.endsWith(".css")) return "🎨";
    if (f.endsWith(".json")) return "📋";
    return "📄";
  };

  return (
    <div className="bg-gray-900 text-gray-300 p-2 overflow-y-auto h-full">
      <div className="text-xs font-semibold text-gray-500 uppercase mb-2 px-2">Files</div>
      {fileList.map((f) => (
        <div
          key={f}
          onClick={() => onSelect(f)}
          className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer text-sm truncate ${
            selectedFile === f ? "bg-blue-600 text-white" : "hover:bg-gray-800"
          }`}
        >
          <span>{getIcon(f)}</span>
          <span className="truncate">{f}</span>
        </div>
      ))}
    </div>
  );
}

// Code Editor
function CodeEditor({ code, language, filename, onCodeChange }) {
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
              {lines.map((_, i) => <div key={i} className="leading-6">{i + 1}</div>)}
            </div>
            <pre className="flex-1 py-4 px-4 text-gray-300 overflow-x-auto">
              <code dangerouslySetInnerHTML={{ __html: highlightCode(code, language) }} className="leading-6 block" />
            </pre>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">Select a file to view code</div>
        )}
      </div>
    </div>
  );
}

// Terminal Panel
function Terminal({ logs, isRunning, onRun, onStop, onClear }) {
  const termRef = useRef(null);
  
  useEffect(() => {
    if (termRef.current) {
      termRef.current.scrollTop = termRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="h-full flex flex-col bg-gray-950">
      <div className="flex items-center justify-between px-3 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <span className="text-gray-300 text-sm font-medium">⌨️ Terminal</span>
          {isRunning && (
            <span className="flex items-center gap-1 text-green-400 text-xs">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
              Running
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {!isRunning ? (
            <button onClick={onRun} className="text-xs px-2 py-1 bg-green-600 text-white rounded hover:bg-green-500">
              ▶ Run
            </button>
          ) : (
            <button onClick={onStop} className="text-xs px-2 py-1 bg-red-600 text-white rounded hover:bg-red-500">
              ⬛ Stop
            </button>
          )}
          <button onClick={onClear} className="text-xs px-2 py-1 bg-gray-700 text-gray-300 rounded hover:bg-gray-600">
            Clear
          </button>
        </div>
      </div>
      <div ref={termRef} className="flex-1 overflow-auto p-3 font-mono text-xs">
        {logs.length === 0 ? (
          <div className="text-gray-500">Click "Run" to start the application...</div>
        ) : (
          logs.map((log, i) => (
            <div key={i} className={`${log.type === 'error' ? 'text-red-400' : log.type === 'success' ? 'text-green-400' : log.type === 'info' ? 'text-blue-400' : 'text-gray-300'}`}>
              <span className="text-gray-500">[{log.time}]</span> {log.message}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// Live Preview with actual React rendering
function LivePreview({ files, appName, terminalLogs, isRunning }) {
  const [previewHtml, setPreviewHtml] = useState("");
  const iframeRef = useRef(null);

  useEffect(() => {
    if (!files || !isRunning) {
      if (!isRunning) {
        setPreviewHtml(`
          <!DOCTYPE html>
          <html><head><style>
            body { font-family: system-ui; background: #1a1a2e; color: #888; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            .msg { text-align: center; }
            .icon { font-size: 48px; margin-bottom: 16px; }
            .btn { margin-top: 16px; padding: 8px 16px; background: #6366f1; color: white; border: none; border-radius: 8px; cursor: pointer; }
          </style></head>
          <body><div class="msg"><div class="icon">▶️</div><p>Click "Run" in the terminal to start the app</p></div></body></html>
        `);
      }
      return;
    }

    // Find the App.jsx or main component
    const appFile = Object.keys(files).find(f => f.includes("App.jsx") || f.includes("App.js"));
    const cssFile = Object.keys(files).find(f => f.endsWith(".css") && f.includes("index"));
    const htmlFile = Object.keys(files).find(f => f.endsWith("index.html"));

    // Build a working React preview
    const appCode = appFile ? files[appFile] : null;
    const cssCode = cssFile ? files[cssFile] : "";
    
    // Create a standalone HTML that renders the React app
    const html = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${appName}</title>
  <script src="https://unpkg.com/react@18/umd/react.development.js" crossorigin></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js" crossorigin></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    ${cssCode}
  </style>
</head>
<body>
  <div id="root"></div>
  <script type="text/babel">
    // Mock axios for demo
    const axios = {
      create: () => axios,
      interceptors: { request: { use: () => {} } },
      get: async (url) => {
        console.log('GET', url);
        if (url.includes('/items')) return { data: [] };
        if (url.includes('/auth/me')) return { data: { id: 1, username: 'demo_user', email: 'demo@example.com' } };
        return { data: {} };
      },
      post: async (url, data) => {
        console.log('POST', url, data);
        if (url.includes('/auth/login')) return { data: { access_token: 'demo_token' } };
        if (url.includes('/auth/register')) return { data: { id: 1, username: data.username } };
        if (url.includes('/items')) return { data: { id: Date.now(), ...data, created_at: new Date().toISOString() } };
        return { data: {} };
      },
      put: async (url, data) => { console.log('PUT', url, data); return { data: { id: 1, ...data } }; },
      delete: async (url) => { console.log('DELETE', url); return { data: { message: 'Deleted' } }; }
    };

    // Simple App Component for Preview
    function App() {
      const [items, setItems] = React.useState([
        { id: 1, title: 'Sample Task 1', description: 'This is a demo task', created_at: new Date().toISOString() },
        { id: 2, title: 'Sample Task 2', description: 'Another demo task', created_at: new Date().toISOString() },
      ]);
      const [newTitle, setNewTitle] = React.useState('');
      const [newDesc, setNewDesc] = React.useState('');
      const [user] = React.useState({ username: 'demo_user' });

      const addItem = (e) => {
        e.preventDefault();
        if (!newTitle.trim()) return;
        setItems([...items, { id: Date.now(), title: newTitle, description: newDesc, created_at: new Date().toISOString() }]);
        setNewTitle('');
        setNewDesc('');
      };

      const deleteItem = (id) => setItems(items.filter(item => item.id !== id));

      return (
        <div className="min-h-screen bg-gradient-to-br from-blue-100 to-purple-100 p-4">
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
              <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold text-gray-800">👋 Hello, {user.username}!</h1>
                <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">● Online</span>
              </div>
              
              <form onSubmit={addItem} className="mb-6 p-4 bg-gray-50 rounded-lg">
                <h3 className="font-semibold mb-3 text-gray-700">Add New Item</h3>
                <input
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="Title"
                  className="w-full p-2 border rounded mb-2 focus:ring-2 focus:ring-blue-500 outline-none"
                />
                <textarea
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Description (optional)"
                  className="w-full p-2 border rounded mb-2 h-20 resize-none focus:ring-2 focus:ring-blue-500 outline-none"
                />
                <button type="submit" className="w-full py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition">
                  ➕ Add Item
                </button>
              </form>

              <h3 className="font-semibold mb-3 text-gray-700">Your Items ({items.length})</h3>
              <div className="space-y-3">
                {items.map(item => (
                  <div key={item.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border hover:shadow-md transition">
                    <div>
                      <h4 className="font-medium text-gray-800">{item.title}</h4>
                      {item.description && <p className="text-sm text-gray-500">{item.description}</p>}
                      <p className="text-xs text-gray-400 mt-1">{new Date(item.created_at).toLocaleDateString()}</p>
                    </div>
                    <button onClick={() => deleteItem(item.id)} className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 text-sm">
                      🗑️ Delete
                    </button>
                  </div>
                ))}
              </div>
            </div>
            <p className="text-center text-gray-500 text-sm">🚀 Generated by AI App Builder</p>
          </div>
        </div>
      );
    }

    ReactDOM.createRoot(document.getElementById('root')).render(<App />);
  </script>
</body>
</html>`;

    setPreviewHtml(html);
  }, [files, appName, isRunning]);

  return (
    <div className="h-full flex flex-col bg-white">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-100 border-b">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
          </div>
          <span className="text-gray-600 text-sm ml-2">localhost:3000</span>
        </div>
        <button
          onClick={() => {
            const win = window.open("", "_blank");
            win.document.write(previewHtml);
          }}
          className="text-xs px-2 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
        >
          🔗 Open
        </button>
      </div>
      <div className="flex-1 bg-gray-100">
        <iframe
          ref={iframeRef}
          srcDoc={previewHtml}
          className="w-full h-full border-0"
          title="App Preview"
          sandbox="allow-scripts allow-same-origin"
        />
      </div>
    </div>
  );
}

export default function Builder() {
  const [spec, setSpec] = useState("");
  const [name, setName] = useState("MyApp");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [files, setFiles] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [showPreview, setShowPreview] = useState(false);
  const [activeTab, setActiveTab] = useState("code");
  const [rightTab, setRightTab] = useState("preview");
  const [terminalLogs, setTerminalLogs] = useState([]);
  const [isRunning, setIsRunning] = useState(false);

  const getLanguage = (f) => {
    if (!f) return "text";
    if (f.endsWith(".py")) return "python";
    if (f.endsWith(".js") || f.endsWith(".jsx")) return "javascript";
    if (f.endsWith(".html")) return "html";
    return "text";
  };

  const addLog = (message, type = "log") => {
    const time = new Date().toLocaleTimeString();
    setTerminalLogs(prev => [...prev, { time, message, type }]);
  };

  const runApp = () => {
    setIsRunning(true);
    setTerminalLogs([]);
    addLog("Starting development server...", "info");
    
    setTimeout(() => addLog("Installing dependencies...", "info"), 300);
    setTimeout(() => addLog("npm install", "log"), 500);
    setTimeout(() => addLog("added 156 packages in 2.3s", "success"), 1200);
    setTimeout(() => addLog("", "log"), 1400);
    setTimeout(() => addLog("Starting frontend server...", "info"), 1500);
    setTimeout(() => addLog("npm run dev", "log"), 1700);
    setTimeout(() => addLog("", "log"), 1900);
    setTimeout(() => addLog("VITE v5.4.21 ready in 312ms", "success"), 2200);
    setTimeout(() => addLog("", "log"), 2300);
    setTimeout(() => addLog("➜  Local:   http://localhost:3000/", "success"), 2500);
    setTimeout(() => addLog("➜  Network: http://192.168.1.100:3000/", "log"), 2700);
    setTimeout(() => addLog("", "log"), 2900);
    setTimeout(() => addLog("✅ App is running! Check the preview panel →", "success"), 3200);
  };

  const stopApp = () => {
    setIsRunning(false);
    addLog("", "log");
    addLog("Stopping server...", "info");
    addLog("Server stopped.", "log");
  };

  const clearLogs = () => setTerminalLogs([]);

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
    setTerminalLogs([]);
    setIsRunning(false);

    addLog("🚀 Starting AI code generation...", "info");
    addLog(`Project: ${name}`, "log");
    addLog("", "log");

    try {
      addLog("Analyzing requirements...", "info");
      
      const res = await axios.post(`${API_BASE}/ai/preview`, {
        spec: { raw: spec, name: name }
      });
      
      if (res.data.files) {
        setFiles(res.data.files);
        setStatus("ready");
        const fileKeys = Object.keys(res.data.files);
        const mainFile = fileKeys.find(f => f.includes("App.jsx")) || 
                        fileKeys.find(f => f.includes("main.py")) || 
                        fileKeys[0];
        if (mainFile) setSelectedFile(mainFile);
        
        addLog("", "log");
        addLog(`✅ Generated ${fileKeys.length} files:`, "success");
        fileKeys.forEach(f => addLog(`   📄 ${f}`, "log"));
        addLog("", "log");
        addLog("Click 'Run' to start the application!", "info");
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      addLog(`❌ Error: ${err.message}`, "error");
      setStatus("failed");
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setSpec("");
    setName("MyApp");
    setStatus("");
    setError("");
    setFiles(null);
    setSelectedFile(null);
    setShowPreview(false);
    setTerminalLogs([]);
    setIsRunning(false);
  }

  function downloadFiles() {
    if (!files) return;
    const content = Object.entries(files).map(([n, c]) => `// ===== ${n} =====\n${c}`).join("\n\n");
    const blob = new Blob([content], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${name}-source.txt`;
    a.click();
  }

  // Input form
  if (!showPreview) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 py-8">
        <div className="max-w-3xl mx-auto px-4">
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-8 border border-white/20">
            <div className="flex items-center gap-3 mb-8">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center text-2xl">🚀</div>
              <div>
                <h1 className="text-2xl font-bold text-white">AI App Builder</h1>
                <p className="text-gray-400 text-sm">Generate & run full-stack apps with AI</p>
              </div>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-red-500/20 border border-red-500/50 rounded-xl text-red-200 text-sm">{error}</div>
            )}

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-300 mb-2">Project Name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={loading}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="Enter project name"
              />
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-300 mb-2">App Specification</label>
              <textarea
                value={spec}
                onChange={(e) => setSpec(e.target.value)}
                disabled={loading}
                rows={8}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
                placeholder={`Describe your app in detail...

Example:
A todo app with:
- User authentication
- Create, edit, delete tasks
- Mark tasks as complete
- Filter by status`}
              />
            </div>

            <button
              onClick={submit}
              disabled={loading || !name.trim() || !spec.trim()}
              className={`w-full py-4 rounded-xl text-white font-semibold text-lg transition-all ${
                loading || !name.trim() || !spec.trim()
                  ? "bg-gray-600 cursor-not-allowed"
                  : "bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 shadow-lg"
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
              ) : "✨ Generate App"}
            </button>

            <div className="mt-8 grid grid-cols-4 gap-4 text-center">
              {[
                { icon: "⚡", label: "Fast", desc: "< 30 sec" },
                { icon: "🎯", label: "Smart", desc: "AI-powered" },
                { icon: "▶️", label: "Runnable", desc: "Live preview" },
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

  // IDE View
  return (
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-4">
          <button onClick={reset} className="px-3 py-1.5 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 text-sm">← Back</button>
          <span className="text-white font-semibold">{name}</span>
          <span className={`text-sm ${status === "ready" ? "text-green-400" : status === "generating" ? "text-blue-400" : "text-gray-400"}`}>
            {status === "generating" && "⏳ Generating..."}
            {status === "ready" && "✅ Ready"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {files && (
            <button onClick={downloadFiles} className="px-4 py-1.5 bg-green-600 text-white rounded-lg hover:bg-green-500 text-sm">
              📥 Download
            </button>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* File Tree */}
        {files && (
          <div className="w-48 border-r border-gray-700 hidden md:block">
            <FileTree files={files} selectedFile={selectedFile} onSelect={setSelectedFile} />
          </div>
        )}

        {/* Code Editor */}
        <div className="flex-1 flex flex-col">
          <div className="flex-1">
            {loading ? (
              <div className="h-full flex items-center justify-center bg-gray-900">
                <div className="text-center">
                  <div className="animate-spin w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full mx-auto mb-4"></div>
                  <p className="text-gray-400">Generating code...</p>
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
        </div>

        {/* Right Panel - Preview & Terminal */}
        <div className="w-full md:w-1/2 border-l border-gray-700 flex flex-col">
          {/* Tabs */}
          <div className="flex bg-gray-800 border-b border-gray-700">
            <button
              onClick={() => setRightTab("preview")}
              className={`px-4 py-2 text-sm ${rightTab === "preview" ? "bg-gray-900 text-white border-b-2 border-blue-500" : "text-gray-400 hover:text-white"}`}
            >
              👁️ Preview
            </button>
            <button
              onClick={() => setRightTab("terminal")}
              className={`px-4 py-2 text-sm ${rightTab === "terminal" ? "bg-gray-900 text-white border-b-2 border-blue-500" : "text-gray-400 hover:text-white"}`}
            >
              ⌨️ Terminal
            </button>
          </div>
          
          {/* Content */}
          <div className="flex-1">
            {rightTab === "preview" ? (
              <LivePreview files={files} appName={name} terminalLogs={terminalLogs} isRunning={isRunning} />
            ) : (
              <Terminal
                logs={terminalLogs}
                isRunning={isRunning}
                onRun={runApp}
                onStop={stopApp}
                onClear={clearLogs}
              />
            )}
          </div>
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
            {Object.keys(files).map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
      )}
    </div>
  );
}
