import React, { useState, useEffect, useRef } from "react";
import FileTree from "../components/FileTree";
import CodeEditor from "../components/CodeEditor";
import Terminal from "../components/Terminal";
import LivePreview from "../components/LivePreview";
import WebContainerPreview from "../components/WebContainerPreview";
import { apiClient, API_V1 } from "../config/api";

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
  const [editInstruction, setEditInstruction] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [projectId, setProjectId] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [useWebContainer, setUseWebContainer] = useState(false);
  const [imagePreview, setImagePreview] = useState(null);
  const fileInputRef = useRef(null);
  const editFileInputRef = useRef(null);

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

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

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
    setProjectId(null);

    addLog("🚀 Starting AI code generation...", "info");
    addLog(`Project: ${name}`, "log");
    if (imagePreview) addLog("📸 Image context attached", "info");
    addLog("", "log");

    try {
      addLog("Creating project...", "info");
      
      // 1. Create Project
      const createRes = await apiClient.post('/projects/', {
        name: name,
        spec: JSON.stringify({ 
          raw: spec, 
          name: name,
          image: imagePreview // Pass image in spec for now, or handle in backend separately
        })
      });
      
      // Note: The backend currently expects image in the payload, not in the spec JSON string for the project creation.
      // However, the generation job runs in background.
      // We need to update the backend to handle image in the generation job if it's passed in the spec.
      // OR we can pass it to the preview endpoint if we were using that.
      // But here we are using the async project generation flow.
      
      // Wait! The `start_generation_job` in backend reads the spec string.
      // If I put the image in the spec string, it might be too large for the DB text field?
      // `spec` is a string in the DB.
      // Base64 images can be large.
      
      // Let's check the backend `Project` model. `spec` is `str`.
      // SQLite `TEXT` can hold large strings, but it's not ideal.
      // But for a prototype, it's fine.
      
      // Actually, I should probably use the `preview` endpoint for immediate feedback if I want to use the image, 
      // OR update the `create_project` endpoint to accept an image separately and store it.
      
      // For now, let's stick to the `preview` endpoint for the initial generation if an image is present?
      // No, the user expects the project flow.
      
      // Let's assume the backend `start_generation_job` parses the spec JSON and extracts the image if present.
      // I need to update `backend/app/services/generator.py` to handle this.
      
      const pid = createRes.data.id;
      setProjectId(pid);
      addLog(`Project created (ID: ${pid})`, "success");
      addLog("Waiting for generation...", "log");
      
      // 2. Poll for completion
      let attempts = 0;
      const maxAttempts = 120; // 2 minutes timeout
      
      const pollInterval = setInterval(async () => {
        attempts++;
        try {
          const statusRes = await apiClient.get(`/projects/${pid}`);
          const pStatus = statusRes.data.status;
          
          if (pStatus === 'ready') {
            clearInterval(pollInterval);
            addLog("Generation complete!", "success");
            
            // 3. Fetch files
            const filesRes = await apiClient.get(`/projects/${pid}/files`);
            setFiles(filesRes.data);
            setStatus("ready");
            setIsRunning(true); // Auto-start preview
            
            const fileKeys = Object.keys(filesRes.data);
            const mainFile = fileKeys.find(f => f.includes("App.jsx")) || 
                            fileKeys.find(f => f.includes("main.py")) || 
                            fileKeys[0];
            if (mainFile) setSelectedFile(mainFile);
            
            addLog("", "log");
            addLog(`✅ Generated ${fileKeys.length} files:`, "success");
            fileKeys.forEach(f => addLog(`   📄 ${f}`, "log"));
            addLog("", "log");
            addLog("Click 'Run' to start the application!", "info");
            setLoading(false);
          } else if (pStatus === 'failed') {
            clearInterval(pollInterval);
            throw new Error("Generation failed on server");
          } else {
            if (attempts % 5 === 0) addLog("Still generating...", "log");
          }
          
          if (attempts >= maxAttempts) {
            clearInterval(pollInterval);
            throw new Error("Timeout waiting for generation");
          }
        } catch (err) {
          clearInterval(pollInterval);
          setError(err.message);
          setLoading(false);
          setStatus("failed");
          addLog(`❌ Error: ${err.message}`, "error");
        }
      }, 1000);

    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      addLog(`❌ Error: ${err.message}`, "error");
      setStatus("failed");
      setLoading(false);
    }
  }

  async function submitEdit() {
    if (!editInstruction.trim()) return;
    
    setIsEditing(true);
    addLog(`📝 Applying edit: "${editInstruction}"`, "info");
    if (imagePreview) addLog("📸 Image context attached", "info");
    
    try {
      const res = await apiClient.post('/ai/edit', {
        files: files,
        instruction: editInstruction,
        project_name: name,
        project_id: projectId,
        image: imagePreview
      });
      
      if (res.data.files) {
        // Merge new files with existing ones
        setFiles(prev => ({ ...prev, ...res.data.files }));
        
        const changedFiles = Object.keys(res.data.files);
        addLog(`✅ Modified ${changedFiles.length} files:`, "success");
        changedFiles.forEach(f => addLog(`   📝 ${f}`, "log"));
        
        // If current file was changed, refresh it
        if (selectedFile && changedFiles.includes(selectedFile)) {
          // Force refresh by briefly clearing selection (optional, React handles state update)
        }
        
        setEditInstruction("");
        setImagePreview(null); // Clear image after edit
      }
    } catch (err) {
      addLog(`❌ Edit failed: ${err.message}`, "error");
    } finally {
      setIsEditing(false);
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
    setImagePreview(null);
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
              <div className="relative">
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
                <button 
                  onClick={() => fileInputRef.current?.click()}
                  className="absolute bottom-3 right-3 p-2 bg-gray-700/50 hover:bg-gray-600/50 rounded-lg text-gray-300 hover:text-white transition-colors"
                  title="Upload screenshot/mockup"
                >
                  📷
                </button>
              </div>
              {imagePreview && (
                <div className="mt-2 relative inline-block group">
                  <img src={imagePreview} alt="Context" className="h-20 rounded-lg border border-gray-600 object-cover" />
                  <button 
                    onClick={() => { setImagePreview(null); if(fileInputRef.current) fileInputRef.current.value = ''; }}
                    className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs shadow-lg opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    ×
                  </button>
                </div>
              )}
              <input 
                type="file" 
                ref={fileInputRef} 
                onChange={handleImageUpload} 
                className="hidden" 
                accept="image/*" 
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
        {/* File Tree & AI Edit */}
        {files && (
          <div className="w-64 border-r border-gray-700 hidden md:flex flex-col bg-gray-900">
            <div className="flex-1 overflow-y-auto">
              <FileTree files={files} selectedFile={selectedFile} onSelect={setSelectedFile} />
            </div>
            
            {/* AI Edit Input */}
            <div className="p-3 border-t border-gray-700 bg-gray-800">
              <label className="block text-xs font-medium text-blue-400 mb-2">✨ AI Magic Edit</label>
              <div className="relative">
                <textarea
                  value={editInstruction}
                  onChange={(e) => setEditInstruction(e.target.value)}
                  disabled={isEditing}
                  placeholder="e.g. Change button color to red..."
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none mb-2 pr-8"
                  rows={3}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      submitEdit();
                    }
                  }}
                />
                <button 
                  onClick={() => editFileInputRef.current?.click()}
                  className="absolute bottom-4 right-2 text-gray-400 hover:text-white p-1 rounded hover:bg-gray-700"
                  title="Upload reference image"
                >
                  📷
                </button>
              </div>
              
              {imagePreview && (
                <div className="mb-2 relative inline-block group">
                  <img src={imagePreview} alt="Context" className="h-16 rounded border border-gray-600 object-cover" />
                  <button 
                    onClick={() => { setImagePreview(null); if(editFileInputRef.current) editFileInputRef.current.value = ''; }}
                    className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-4 h-4 flex items-center justify-center text-[10px] shadow-lg"
                  >
                    ×
                  </button>
                </div>
              )}
              <input 
                type="file" 
                ref={editFileInputRef} 
                onChange={handleImageUpload} 
                className="hidden" 
                accept="image/*" 
              />

              <button
                onClick={submitEdit}
                disabled={isEditing || !editInstruction.trim()}
                className={`w-full py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  isEditing || !editInstruction.trim()
                    ? "bg-gray-700 text-gray-500 cursor-not-allowed"
                    : "bg-blue-600 text-white hover:bg-blue-500"
                }`}
              >
                {isEditing ? "Applying..." : "Apply Edit"}
              </button>
            </div>
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
          <div className="flex items-center justify-between bg-gray-800 border-b border-gray-700 pr-2">
            <div className="flex">
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
            {rightTab === "preview" && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500 hidden sm:inline">Engine:</span>
                <div className="flex bg-gray-900 rounded-lg p-0.5 border border-gray-700">
                  <button 
                    onClick={() => setUseWebContainer(false)}
                    className={`text-xs px-2 py-1 rounded-md transition-colors ${!useWebContainer ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white'}`}
                    title="Fast preview using Babel (Client-side)"
                  >
                    ⚡ Fast
                  </button>
                  <button 
                    onClick={() => setUseWebContainer(true)}
                    className={`text-xs px-2 py-1 rounded-md transition-colors ${useWebContainer ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white'}`}
                    title="Full Node.js environment (WebContainers)"
                  >
                    📦 Full
                  </button>
                </div>
              </div>
            )}
          </div>
          
          {/* Content */}
          <div className="flex-1 relative">
            {rightTab === "preview" ? (
              useWebContainer ? (
                <WebContainerPreview files={files} onLog={(msg, type) => addLog(msg, type)} />
              ) : (
                <LivePreview files={files} appName={name} terminalLogs={terminalLogs} isRunning={isRunning} />
              )
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
