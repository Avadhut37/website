import React, { useState, useEffect, useRef } from "react";

export default function LivePreview({ files, appName, terminalLogs, isRunning }) {
  const [previewHtml, setPreviewHtml] = useState("");
  const iframeRef = useRef(null);

  useEffect(() => {
    // If no files yet, show loading or waiting state
    if (!files) {
      setPreviewHtml(`
        <!DOCTYPE html>
        <html><head><style>
          body { font-family: system-ui; background: #1a1a2e; color: #888; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
          .msg { text-align: center; }
          .spinner { width: 48px; height: 48px; border: 4px solid #333; border-top-color: #6366f1; border-radius: 50%; animation: spin 1s linear infinite; }
          @keyframes spin { to { transform: rotate(360deg); } }
        </style></head>
        <body><div class="msg"><div class="spinner"></div><p style="margin-top: 16px;">Waiting for code...</p></div></body></html>
      `);
      return;
    }
    
    console.log('📦 LivePreview received files:', Object.keys(files));

    // Find all JS/JSX files in frontend/src
    const componentFiles = Object.keys(files).filter(f => 
      (f.includes("frontend/src/") || f.startsWith("src/")) && 
      (f.endsWith(".jsx") || f.endsWith(".js")) &&
      !f.includes("main.jsx") && // Exclude entry point
      !f.includes("vite.config")
    );

    // Sort files to put App.jsx last (naive dependency resolution)
    componentFiles.sort((a, b) => {
      if (a.includes("App.jsx")) return 1;
      if (b.includes("App.jsx")) return -1;
      return 0;
    });

    const cssFile = Object.keys(files).find(f => 
      (f.includes("frontend") || f.includes("src")) && 
      (f.includes("index.css") || f.includes("App.css") || f.endsWith(".css"))
    );
    
    const cssCode = cssFile ? files[cssFile] : "";
    
    // Bundle code: Concatenate all components
    let bundledCode = "";
    
    componentFiles.forEach(file => {
      let code = files[file];
      
      // 1. Handle Lucide React imports
      // Replace: import { X, Y } from 'lucide-react' -> const { X, Y } = window.LucideReact;
      code = code.replace(/import\s+\{(.*?)\}\s+from\s+['"]lucide-react['"]\s*;?/g, 'const {$1} = window.LucideReact;');
      
      // 2. Remove other imports
      code = code.replace(/import\s+.*?from\s+['"].*?['"]\s*;?\s*/g, '');
      
      // 3. Remove export default and named exports
      code = code.replace(/export\s+default\s+/g, '');
      code = code.replace(/export\s+/g, '');
      
      // 4. Add file comment
      bundledCode += `\n// --- ${file} ---\n${code}\n`;
    });
    
    // If no code found from component files, check for any App file
    if (!bundledCode.trim() || !bundledCode.includes('App')) {
      console.log('⚠️ No App component found in frontend/src, searching all files...');
      
      // Try to find App.jsx anywhere
      const appFile = Object.keys(files).find(f => 
        f.endsWith('App.jsx') || f.endsWith('App.js')
      );
      
      if (appFile) {
        let code = files[appFile];
        code = code.replace(/import\s+\{(.*?)\}\s+from\s+['"]lucide-react['"]\s*;?/g, 'const {$1} = window.LucideReact;');
        code = code.replace(/import\s+.*?from\s+['"].*?['"]\s*;?\s*/g, '');
        code = code.replace(/export\s+default\s+/g, '');
        code = code.replace(/export\s+/g, '');
        bundledCode = `\n// --- ${appFile} ---\n${code}\n`;
        console.log('✅ Found App file:', appFile);
      } else {
        console.log('⚠️ No App file found, using fallback demo');
        bundledCode = `
    // Fallback Demo App
    function App() {
      const [items, setItems] = React.useState([]);
      const [title, setTitle] = React.useState('');

      const addItem = (e) => {
        e.preventDefault();
        if (!title.trim()) return;
        const newItem = { id: Date.now(), title, created_at: new Date().toISOString() };
        setItems([...items, newItem]);
        setTitle('');
      };

      const deleteItem = (id) => setItems(items.filter(i => i.id !== id));

      return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 p-6">
          <div className="max-w-md mx-auto">
            <h1 className="text-2xl font-bold text-gray-800 mb-6">${appName || 'My App'}</h1>
            <form onSubmit={addItem} className="mb-4 flex gap-2">
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Add new item..."
                className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                Add
              </button>
            </form>
            <div className="space-y-2">
              {items.map(item => (
                <div key={item.id} className="flex justify-between items-center p-3 bg-white rounded-lg shadow">
                  <span>{item.title}</span>
                  <button onClick={() => deleteItem(item.id)} className="text-red-500 hover:text-red-700">
                    ✕
                  </button>
                </div>
              ))}
              {items.length === 0 && (
                <p className="text-center text-gray-400 py-8">No items yet. Add one above!</p>
              )}
            </div>
          </div>
        </div>
      );
    }
        `;
      }
    }
    
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
  <!-- Lucide Icons (Mock) -->
  <script>
    // Mock Lucide React
    const LucideIcons = new Proxy({}, {
      get: (target, prop) => {
        return (props) => {
          // Return an SVG placeholder
          return React.createElement('svg', {
            ...props,
            width: props.size || 24,
            height: props.size || 24,
            viewBox: "0 0 24 24",
            fill: "none",
            stroke: props.color || "currentColor",
            strokeWidth: props.strokeWidth || 2,
            strokeLinecap: "round",
            strokeLinejoin: "round"
          }, React.createElement('rect', { x: 2, y: 2, width: 20, height: 20, rx: 5 }));
        }
      }
    });
    // Expose as global for "import { X } from 'lucide-react'" shim
    window.LucideReact = LucideIcons;
  </script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: system-ui, -apple-system, sans-serif; }
    ${cssCode}
  </style>
</head>
<body>
  <div id="root"></div>
  <script type="text/babel">
    // Shim for React hooks and common imports
    const { useState, useEffect, useRef, useCallback, useMemo, useContext, useReducer } = React;
    
    // Shim for Lucide React (since we strip imports, we need to make the icons available globally if they are used as named imports)
    // But wait, if we strip "import { Home } from 'lucide-react'", "Home" is undefined.
    // We need to inject these variables.
    // Since we don't know which icons are used, we can't easily pre-define them.
    // A better approach: Regex replace "import { X, Y } from 'lucide-react'" with "const { X, Y } = window.LucideReact;"
    
    // Mock axios with In-Memory DB
    const db = {
      items: [],
      tasks: [],
      users: [{ id: 1, username: 'demo', email: 'demo@example.com' }],
      posts: [],
      products: [],
      notes: [],
      todos: []
    };
    
    // Helper to get collection name from URL
    const getCollection = (url) => {
      const match = url.match(/\\/(items|tasks|todos|posts|products|notes|users)(?:\\/|$|\\?)/i);
      return match ? match[1].toLowerCase() : 'items';
    };

    const axios = {
      create: () => axios,
      defaults: { headers: { common: {} } },
      interceptors: { request: { use: () => {} }, response: { use: () => {} } },
      get: async (url) => {
        console.log('🔵 GET', url);
        await new Promise(r => setTimeout(r, 200)); // Simulate latency
        
        // Auth endpoints
        if (url.includes('/auth/me') || url.includes('/users/me')) return { data: db.users[0] };
        if (url.includes('/health')) return { data: { status: 'ok' } };
        
        // Get single item by ID
        const idMatch = url.match(/\\/(\\w+)\\/(\\d+)$/);
        if (idMatch) {
          const col = idMatch[1].toLowerCase();
          const id = parseInt(idMatch[2]);
          const collection = db[col] || db.items;
          const item = collection.find(i => i.id === id);
          return { data: item || null };
        }
        
        // Get collection
        const collection = getCollection(url);
        return { data: db[collection] || [] };
      },
      post: async (url, data) => {
        console.log('🟢 POST', url, data);
        await new Promise(r => setTimeout(r, 200));
        
        // Auth endpoints
        if (url.includes('/auth/login') || url.includes('/login')) {
          return { data: { access_token: 'demo_token', token: 'demo_token', user: db.users[0] } };
        }
        if (url.includes('/auth/register') || url.includes('/register')) {
          return { data: { id: Date.now(), ...data, token: 'demo_token' } };
        }
        
        // Create item in collection
        const collection = getCollection(url);
        const newItem = { 
          id: Date.now(), 
          ...data, 
          created_at: new Date().toISOString(),
          completed: data.completed || false
        };
        db[collection] = db[collection] || [];
        db[collection].push(newItem);
        return { data: newItem };
      },
      put: async (url, data) => { 
        console.log('🟡 PUT', url, data);
        await new Promise(r => setTimeout(r, 200));
        
        const idMatch = url.match(/\\/(\\w+)\\/(\\d+)$/);
        if (idMatch) {
          const col = idMatch[1].toLowerCase();
          const id = parseInt(idMatch[2]);
          const collection = db[col] || db.items;
          const idx = collection.findIndex(i => i.id === id);
          if (idx !== -1) {
            collection[idx] = { ...collection[idx], ...data, updated_at: new Date().toISOString() };
            return { data: collection[idx] };
          }
        }
        return { data: { id: 1, ...data, updated_at: new Date().toISOString() } }; 
      },
      patch: async (url, data) => { 
        console.log('🟠 PATCH', url, data);
        // Same as PUT for simplicity
        return axios.put(url, data);
      },
      delete: async (url) => { 
        console.log('🔴 DELETE', url); 
        await new Promise(r => setTimeout(r, 200));
        
        const idMatch = url.match(/\\/(\\w+)\\/(\\d+)$/);
        if (idMatch) {
          const col = idMatch[1].toLowerCase();
          const id = parseInt(idMatch[2]);
          if (db[col]) {
            db[col] = db[col].filter(i => i.id !== id);
          }
        }
        return { data: { message: 'Deleted', success: true } }; 
      }
    };

    ${bundledCode}

    try {
      const root = ReactDOM.createRoot(document.getElementById('root'));
      root.render(<App />);
    } catch (error) {
      console.error('Preview render error:', error);
      document.getElementById('root').innerHTML = \`
        <div style="padding: 20px; background: #fee; color: #c00; border-radius: 8px; margin: 20px;">
          <h3>⚠️ Preview Error</h3>
          <p>\${error.message}</p>
          <pre style="margin-top: 10px; font-size: 11px; overflow: auto;">\${error.stack}</pre>
        </div>
      \`;
    }
  </script>
</body>
</html>`;

    setPreviewHtml(html);
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
