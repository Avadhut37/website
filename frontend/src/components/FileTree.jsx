import React from "react";

export default function FileTree({ files, selectedFile, onSelect }) {
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
