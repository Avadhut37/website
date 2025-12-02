import React from "react";

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

export default function CodeEditor({ code, language, filename, onCodeChange }) {
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
