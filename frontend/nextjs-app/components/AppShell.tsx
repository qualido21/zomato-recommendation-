'use client';

import { useState } from 'react';
import PreferenceForm from '@/components/PreferenceForm';
import ResultsPanel from '@/components/ResultsPanel';
import type { RecommendResponse } from '@/lib/api';

interface AppShellProps {
  locations: string[];
  cuisines: string[];
  llmProvider: string;
}

export default function AppShell({ locations, cuisines, llmProvider }: AppShellProps) {
  const [result, setResult] = useState<RecommendResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function handleResult(data: RecommendResponse) {
    setResult(data);
    setError(null);
  }

  function handleError(msg: string) {
    setError(msg);
    setResult(null);
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-8">
      {/* LEFT — Preferences */}
      <aside>
        {/* LLM badge */}
        <div className="flex items-center gap-2 mb-5">
          <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-xs text-white/40">
            Connected · LLM: <strong className="text-white/70">{llmProvider.toUpperCase()}</strong>
          </span>
        </div>

        <div className="bg-[#141414] border border-white/8 rounded-2xl p-5">
          <h2 className="font-serif text-lg font-bold mb-5 text-white">Your Preferences</h2>
          <PreferenceForm
            locations={locations}
            cuisines={cuisines}
            onResult={handleResult}
            onError={handleError}
            onLoading={setLoading}
          />
        </div>

        {/* Editorial tagline */}
        <p className="text-white/20 text-xs text-center mt-4 leading-relaxed">
          Curated by AI · Powered by Groq LLM<br />
          Bangalore restaurant dataset · {locations.length} localities
        </p>
      </aside>

      {/* RIGHT — Results */}
      <main>
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-serif text-lg font-bold text-white">
            {result ? 'Recommendations' : 'Discover Restaurants'}
          </h2>
          {result && (
            <button
              onClick={() => { setResult(null); setError(null); }}
              className="text-xs text-white/40 hover:text-white transition-colors"
            >
              Clear ×
            </button>
          )}
        </div>
        <ResultsPanel data={result} error={error} loading={loading} />
      </main>
    </div>
  );
}
