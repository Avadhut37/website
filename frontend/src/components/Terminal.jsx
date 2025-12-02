import React, { useEffect, useRef } from "react";

export default function Terminal({ logs, isRunning, onRun, onStop, onClear }) {
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
