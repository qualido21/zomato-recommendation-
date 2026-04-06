'use client';

import { useState, useTransition } from 'react';
import { Search, ChevronDown, Star, Wallet } from 'lucide-react';
import { recommend, type RecommendRequest, type RecommendResponse } from '@/lib/api';

interface PreferenceFormProps {
  locations: string[];
  cuisines: string[];
  onResult: (data: RecommendResponse) => void;
  onError: (msg: string) => void;
  onLoading: (v: boolean) => void;
}

export default function PreferenceForm({
  locations,
  cuisines,
  onResult,
  onError,
  onLoading,
}: PreferenceFormProps) {
  const [city, setCity] = useState(locations.includes('Indiranagar') ? 'Indiranagar' : locations[0] ?? '');
  const [budgetMax, setBudgetMax] = useState(800);
  const [selectedCuisines, setSelectedCuisines] = useState<string[]>([]);
  const [minRating, setMinRating] = useState(3.5);
  const [extraPrefs, setExtraPrefs] = useState('');
  const [cuisineSearch, setCuisineSearch] = useState('');
  const [showCuisineDropdown, setShowCuisineDropdown] = useState(false);
  const [isPending, startTransition] = useTransition();

  const filteredCuisines = cuisines.filter(
    (c) => c.toLowerCase().includes(cuisineSearch.toLowerCase()) && !selectedCuisines.includes(c)
  );

  function toggleCuisine(c: string) {
    setSelectedCuisines((prev) =>
      prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]
    );
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const req: RecommendRequest = {
      city,
      budget_max: budgetMax,
      cuisines: selectedCuisines,
      min_rating: minRating,
      extra_prefs: extraPrefs,
    };

    onLoading(true);
    startTransition(async () => {
      try {
        const data = await recommend(req);
        onResult(data);
      } catch (err) {
        onError(err instanceof Error ? err.message : 'Something went wrong');
      } finally {
        onLoading(false);
      }
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Locality */}
      <div>
        <label className="block text-xs font-semibold text-white/50 uppercase tracking-widest mb-2">
          Locality
        </label>
        <div className="relative">
          <select
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white appearance-none cursor-pointer focus:outline-none focus:border-crimson/50 focus:bg-white/8 transition-all"
          >
            {locations.map((loc) => (
              <option key={loc} value={loc} className="bg-[#1a1a1a]">
                {loc}
              </option>
            ))}
          </select>
          <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none" />
        </div>
      </div>

      {/* Cuisine multi-select */}
      <div>
        <label className="block text-xs font-semibold text-white/50 uppercase tracking-widest mb-2">
          Cuisine(s)
        </label>
        <div className="relative">
          <div
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 cursor-pointer flex items-center gap-2 min-h-[46px] flex-wrap"
            onClick={() => setShowCuisineDropdown((v) => !v)}
          >
            <Search size={13} className="text-white/30 flex-shrink-0" />
            {selectedCuisines.length === 0 ? (
              <span className="text-sm text-white/30">Any cuisine — type to search</span>
            ) : (
              selectedCuisines.map((c) => (
                <span
                  key={c}
                  onClick={(e) => { e.stopPropagation(); toggleCuisine(c); }}
                  className="bg-crimson/20 border border-crimson/40 text-crimson text-xs px-2 py-0.5 rounded-full cursor-pointer hover:bg-crimson/30 transition-colors"
                >
                  {c} ×
                </span>
              ))
            )}
          </div>
          {showCuisineDropdown && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-[#1a1a1a] border border-white/10 rounded-xl overflow-hidden z-20 shadow-xl">
              <div className="p-2 border-b border-white/5">
                <input
                  type="text"
                  value={cuisineSearch}
                  onChange={(e) => setCuisineSearch(e.target.value)}
                  placeholder="Search cuisines..."
                  className="w-full bg-white/5 rounded-lg px-3 py-1.5 text-sm text-white placeholder-white/30 focus:outline-none"
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
              <div className="max-h-44 overflow-y-auto">
                {filteredCuisines.slice(0, 30).map((c) => (
                  <div
                    key={c}
                    onClick={() => { toggleCuisine(c); setCuisineSearch(''); }}
                    className="px-4 py-2 text-sm text-white/70 hover:bg-white/5 hover:text-white cursor-pointer transition-colors"
                  >
                    {c}
                  </div>
                ))}
                {filteredCuisines.length === 0 && (
                  <div className="px-4 py-3 text-sm text-white/30">No cuisines found</div>
                )}
              </div>
            </div>
          )}
        </div>
        {showCuisineDropdown && (
          <div className="fixed inset-0 z-10" onClick={() => setShowCuisineDropdown(false)} />
        )}
      </div>

      {/* Budget */}
      <div>
        <label className="block text-xs font-semibold text-white/50 uppercase tracking-widest mb-2">
          <Wallet size={12} className="inline mr-1.5" />
          Max Budget (₹ for two)
        </label>
        <div className="flex items-center gap-3">
          <input
            type="range"
            min={100}
            max={5000}
            step={100}
            value={budgetMax}
            onChange={(e) => setBudgetMax(Number(e.target.value))}
            className="flex-1 accent-crimson cursor-pointer"
          />
          <span className="text-sm font-bold text-crimson w-16 text-right">₹{budgetMax.toLocaleString()}</span>
        </div>
      </div>

      {/* Min Rating */}
      <div>
        <label className="block text-xs font-semibold text-white/50 uppercase tracking-widest mb-2">
          <Star size={12} className="inline mr-1.5" />
          Minimum Rating — {minRating.toFixed(1)} ⭐
        </label>
        <input
          type="range"
          min={0}
          max={5}
          step={0.1}
          value={minRating}
          onChange={(e) => setMinRating(Number(e.target.value))}
          className="w-full accent-crimson cursor-pointer"
        />
      </div>

      {/* Extra prefs */}
      <div>
        <label className="block text-xs font-semibold text-white/50 uppercase tracking-widest mb-2">
          Additional Preferences
        </label>
        <input
          type="text"
          value={extraPrefs}
          onChange={(e) => setExtraPrefs(e.target.value)}
          placeholder="e.g. family-friendly, outdoor seating, romantic"
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-white/30 focus:outline-none focus:border-crimson/50 transition-all"
        />
      </div>

      <button
        type="submit"
        disabled={isPending}
        className="w-full bg-crimson hover:bg-crimson/90 disabled:opacity-60 text-white font-semibold py-3 rounded-xl flex items-center justify-center gap-2 transition-all text-sm tracking-wide"
      >
        {isPending ? (
          <>
            <span className="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white" />
            Finding...
          </>
        ) : (
          <>
            <Search size={15} />
            Find Restaurants
          </>
        )}
      </button>
    </form>
  );
}
