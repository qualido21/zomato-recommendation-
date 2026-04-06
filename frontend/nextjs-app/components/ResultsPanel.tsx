'use client';

import { AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';
import RestaurantCard from '@/components/RestaurantCard';
import type { RecommendResponse } from '@/lib/api';

interface ResultsPanelProps {
  data: RecommendResponse | null;
  error: string | null;
  loading: boolean;
}

export default function ResultsPanel({ data, error, loading }: ResultsPanelProps) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <div className="w-10 h-10 rounded-full border-2 border-crimson/30 border-t-crimson animate-spin" />
        <p className="text-white/40 text-sm">Finding the best restaurants for you...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
        <div className="w-12 h-12 rounded-full bg-red-900/20 border border-red-500/30 flex items-center justify-center">
          <AlertTriangle size={20} className="text-red-400" />
        </div>
        <p className="text-red-400 font-semibold text-sm">{error}</p>
        <p className="text-white/30 text-xs max-w-xs">Try changing your filters or selecting a different locality.</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3 text-center">
        <div className="w-16 h-16 rounded-full bg-white/3 border border-white/8 flex items-center justify-center mb-2">
          <span className="text-3xl">🍽️</span>
        </div>
        <p className="text-white/50 text-sm font-medium">Set your preferences and click <strong className="text-white">Find Restaurants</strong></p>
        <p className="text-white/25 text-xs">Powered by Groq LLM · Zomato Bangalore dataset</p>
      </div>
    );
  }

  const { recommendations: recs, total_candidates, filters_relaxed, llm_used, message } = data;

  return (
    <div>
      {/* Summary bar */}
      <div className="flex items-center gap-3 mb-5 flex-wrap">
        <div className="flex items-center gap-1.5 text-xs text-white/50">
          <CheckCircle size={12} className="text-green-400" />
          <span><strong className="text-white">{total_candidates}</strong> restaurants matched</span>
        </div>
        {filters_relaxed && (
          <span className="flex items-center gap-1 text-xs bg-yellow-900/20 border border-yellow-500/30 text-yellow-400 px-2 py-0.5 rounded-full">
            <AlertTriangle size={10} />
            Filters relaxed
          </span>
        )}
        {!llm_used && (
          <span className="flex items-center gap-1 text-xs bg-blue-900/20 border border-blue-500/30 text-blue-400 px-2 py-0.5 rounded-full">
            <RefreshCw size={10} />
            AI fallback
          </span>
        )}
        <span className="text-xs text-white/30 ml-auto">
          Showing top <strong className="text-white">{recs.length}</strong>
        </span>
      </div>

      {/* Relaxed-filter message */}
      {message && message !== 'no_results' && (
        <div className="bg-yellow-900/15 border border-yellow-500/20 rounded-xl px-4 py-3 text-xs text-yellow-300/80 mb-4">
          {message}
        </div>
      )}

      {/* Cards */}
      <div className="space-y-5">
        {recs.map((rec, i) => (
          <RestaurantCard key={`${rec.name}-${rec.rank}`} rec={rec} isTop={i === 0} />
        ))}
      </div>
    </div>
  );
}
