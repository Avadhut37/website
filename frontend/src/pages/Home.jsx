import React from "react";
import { Link } from "react-router-dom";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-4xl mx-auto px-4 py-16">
        <div className="text-center">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            🚀 iStudiox
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            AI-powered app builder — generate full-stack applications with intelligent agents.
            Describe your idea, and we'll create the code.
          </p>
          
          <Link 
            to="/builder" 
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white text-lg font-medium rounded-lg hover:bg-blue-700 transition-colors shadow-lg hover:shadow-xl"
          >
            Start Building
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </Link>
        </div>

        <div className="mt-16 grid md:grid-cols-3 gap-6">
          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="text-3xl mb-3">🤖</div>
            <h3 className="font-semibold text-lg mb-2">Multi-Agent System</h3>
            <p className="text-gray-600 text-sm">
              Specialized agents for UI, backend, logic, debugging, and deployment work together.
            </p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="text-3xl mb-3">⚡</div>
            <h3 className="font-semibold text-lg mb-2">Full-Stack Generation</h3>
            <p className="text-gray-600 text-sm">
              Generate complete FastAPI + React projects with proper structure and best practices.
            </p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="text-3xl mb-3">📦</div>
            <h3 className="font-semibold text-lg mb-2">Download & Run</h3>
            <p className="text-gray-600 text-sm">
              Get your generated project as a ZIP file, ready to customize and deploy.
            </p>
          </div>
        </div>

        <div className="mt-12 text-center text-gray-500 text-sm">
          Built with FastAPI • React • TailwindCSS
        </div>
      </div>
    </div>
  );
}
