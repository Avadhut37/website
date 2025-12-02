import React, { useEffect, useRef, useState } from 'react';
import { WebContainer } from '@webcontainer/api';

function convertFilesToTree(files) {
  const tree = {};
  
  Object.entries(files).forEach(([path, content]) => {
    // Remove leading slash if present
    const cleanPath = path.startsWith('/') ? path.slice(1) : path;
    const parts = cleanPath.split('/');
    let current = tree;
    
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      if (i === parts.length - 1) {
        // File
        current[part] = { file: { contents: content } };
      } else {
        // Directory
        if (!current[part]) {
          current[part] = { directory: {} };
        }
        current = current[part].directory;
      }
    }
  });
  
  return tree;
}

export default function WebContainerPreview({ files, terminalLogs, onLog }) {
  const iframeRef = useRef(null);
  const [instance, setInstance] = useState(null);
  const [url, setUrl] = useState('');
  const [status, setStatus] = useState('booting'); // booting, mounting, installing, running, error
  const [error, setError] = useState('');
  const mountedRef = useRef(false);

  // Boot WebContainer once
  useEffect(() => {
    if (mountedRef.current) return;
    mountedRef.current = true;

    async function boot() {
      try {
        onLog?.("Booting WebContainer...", "info");
        const webcontainer = await WebContainer.boot();
        setInstance(webcontainer);
        setStatus('ready');
        onLog?.("WebContainer booted successfully", "success");
      } catch (err) {
        console.error(err);
        setError(err.message);
        setStatus('error');
        onLog?.(`WebContainer boot failed: ${err.message}`, "error");
      }
    }
    boot();
  }, []);

  // Run project when files change
  useEffect(() => {
    if (!instance || !files || Object.keys(files).length === 0 || status === 'installing' || status === 'running') return;

    async function run() {
      try {
        setStatus('mounting');
        onLog?.("Mounting files...", "info");
        
        const tree = convertFilesToTree(files);
        await instance.mount(tree);
        
        // Detect frontend directory
        let cwd = '.';
        if (files['frontend/package.json']) {
          cwd = 'frontend';
        } else if (files['package.json']) {
          cwd = '.';
        } else {
          // Search for any package.json
          const pkgPath = Object.keys(files).find(f => f.endsWith('package.json'));
          if (pkgPath) {
            const pathParts = pkgPath.split('/').slice(0, -1);
            cwd = pathParts.length > 0 ? pathParts.join('/') : '.';
          } else {
            throw new Error("No package.json found in generated files. Files: " + Object.keys(files).join(', '));
          }
        }
        
        // Ensure cwd is not empty
        if (!cwd || cwd === '') cwd = '.';

        onLog?.(`Detected frontend directory: ${cwd || '(root)'}`, "info");

        setStatus('installing');
        onLog?.("Installing dependencies (this may take a while)...", "info");
        
        const installProcess = await instance.spawn('npm', ['install'], { cwd });
        
        installProcess.output.pipeTo(new WritableStream({
          write(data) {
            onLog?.(data, "log");
          }
        }));

        const installExit = await installProcess.exit;
        if (installExit !== 0) {
          throw new Error(`npm install failed with code ${installExit}`);
        }
        
        onLog?.("Dependencies installed", "success");

        setStatus('running');
        onLog?.("Starting dev server...", "info");
        
        const devProcess = await instance.spawn('npm', ['run', 'dev'], { cwd });
        
        devProcess.output.pipeTo(new WritableStream({
          write(data) {
            onLog?.(data, "log");
          }
        }));

        instance.on('server-ready', (port, url) => {
          onLog?.(`Server ready at ${url}`, "success");
          setUrl(url);
        });

      } catch (err) {
        console.error(err);
        setError(err.message);
        setStatus('error');
        onLog?.(`Error: ${err.message}`, "error");
      }
    }

    run();
  }, [instance, files]); // Re-run if files change? Ideally we should just update files.

  return (
    <div className="h-full flex flex-col bg-gray-900">
      <div className="bg-gray-800 text-gray-300 px-4 py-2 text-xs flex justify-between items-center border-b border-gray-700">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${
            status === 'running' ? 'bg-green-500' : 
            status === 'error' ? 'bg-red-500' : 
            'bg-yellow-500'
          }`}></span>
          <span className="uppercase font-semibold">{status}</span>
        </div>
        <div className="truncate max-w-md opacity-50">{url}</div>
      </div>
      
      {error && (
        <div className="p-4 text-red-400 bg-red-900/20 m-4 rounded-lg border border-red-900/50">
          {error}
          <div className="text-xs mt-2 opacity-75">
            Note: WebContainers require a secure context (HTTPS) and specific headers.
            If running locally, ensure headers are configured.
          </div>
        </div>
      )}

      {url ? (
        <iframe 
          src={url} 
          className="flex-1 bg-white w-full h-full border-none" 
          title="WebContainer Preview"
        />
      ) : (
        <div className="flex-1 flex items-center justify-center text-gray-500 flex-col gap-4">
          <div className="animate-pulse text-4xl">⚡</div>
          <p>Initializing WebContainer Environment...</p>
          <p className="text-xs max-w-xs text-center opacity-50">
            This runs a full Node.js environment in your browser.
            First load may take 30-60 seconds.
          </p>
        </div>
      )}
    </div>
  );
}
