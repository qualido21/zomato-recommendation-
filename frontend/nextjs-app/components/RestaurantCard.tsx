'use client';

import { Sparkles, MapPin, Star, BadgeCheck } from 'lucide-react';
import TasteProfileBar from '@/components/TasteProfileBar';
import type { Recommendation } from '@/lib/api';

interface RestaurantCardProps {
  rec: Recommendation;
  isTop?: boolean;
}

// Derive pseudo taste-profile scores deterministically from available data
function deriveProfile(rec: Recommendation) {
  const rating = rec.rating ?? 3.5;
  const spice = Math.round(((rating - 1) / 4) * 60 + 30 + (rec.rank % 3) * 8);
  const fusion = Math.round(50 + (rec.name.charCodeAt(0) % 30));
  const value = Math.round(Math.min(99, ((rating / 5) * 70) + 25));
  return {
    spice: Math.min(99, spice),
    fusion: Math.min(99, fusion),
    value: Math.min(99, value),
  };
}

// Map cuisine to a gradient for the hero
const CUISINE_GRADIENTS: Record<string, string> = {
  italian: 'from-amber-900/80 via-red-900/60 to-stone-900/80',
  chinese: 'from-red-900/80 via-orange-900/60 to-stone-900/80',
  indian: 'from-orange-900/80 via-yellow-900/60 to-stone-900/80',
  continental: 'from-slate-800/80 via-zinc-800/60 to-stone-900/80',
  cafe: 'from-stone-800/80 via-amber-900/60 to-stone-900/80',
};

function heroGradient(cuisine: string) {
  const key = Object.keys(CUISINE_GRADIENTS).find((k) => cuisine.toLowerCase().includes(k));
  return key ? CUISINE_GRADIENTS[key] : 'from-zinc-800/80 via-slate-800/60 to-stone-900/80';
}

export default function RestaurantCard({ rec, isTop = false }: RestaurantCardProps) {
  const profile = deriveProfile(rec);
  const cuisines = rec.cuisine.split(',').map((c) => c.trim());
  const gradient = heroGradient(rec.cuisine);

  return (
    <article className={`rounded-2xl overflow-hidden border border-white/8 bg-[#141414] ${isTop ? 'ring-1 ring-crimson/30' : ''}`}>
      {/* Hero */}
      <div className={`relative h-40 bg-gradient-to-br ${gradient} flex items-end p-5`}>
        {/* Rank badge */}
        <div className="absolute top-4 left-4 flex gap-2">
          <span className="bg-black/60 backdrop-blur-sm text-white text-[10px] font-bold px-2.5 py-1 rounded-full border border-white/20 tracking-widest uppercase">
            #{rec.rank}
          </span>
          {isTop && (
            <span className="bg-crimson text-white text-[10px] font-bold px-2.5 py-1 rounded-full tracking-widest uppercase flex items-center gap-1">
              <BadgeCheck size={10} />
              AI Top Match
            </span>
          )}
        </div>

        {/* Rating badge */}
        {rec.rating && (
          <div className="absolute top-4 right-4 bg-black/60 backdrop-blur-sm flex items-center gap-1 text-xs px-2.5 py-1 rounded-full border border-white/20">
            <Star size={10} className="text-yellow-400 fill-yellow-400" />
            <span className="font-bold text-white">{rec.rating.toFixed(1)}</span>
          </div>
        )}

        {/* Name */}
        <div>
          <h3 className="font-serif text-xl font-bold text-white leading-tight drop-shadow-lg">{rec.name}</h3>
          <p className="text-white/60 text-xs mt-0.5">{cuisines.slice(0, 3).join(' · ')}</p>
        </div>
      </div>

      {/* Body */}
      <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Left — AI Insight */}
        {rec.explanation ? (
          <div className="rounded-xl bg-gradient-to-br from-purple-900/30 via-violet-900/20 to-indigo-900/30 border border-purple-500/20 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles size={13} className="text-purple-400" />
              <span className="text-[10px] font-bold text-purple-400 uppercase tracking-widest">Taste Assistant Insight</span>
            </div>
            <p className="text-white/80 text-xs leading-relaxed">
              <strong className="text-white text-sm block mb-1">Why {rec.name} is for you</strong>
              {rec.explanation}
            </p>
          </div>
        ) : (
          <div className="rounded-xl bg-white/3 border border-white/8 p-4 flex items-center justify-center">
            <p className="text-white/25 text-xs text-center">AI insight unavailable — showing filter result</p>
          </div>
        )}

        {/* Right — Taste Profile + meta */}
        <div>
          <p className="text-[10px] font-bold text-white/40 uppercase tracking-widest mb-3">Taste Profile Analysis</p>
          <TasteProfileBar label="Spice Affinity" value={profile.spice} />
          <TasteProfileBar label="Fusion Preference" value={profile.fusion} color="#a855f7" />
          <TasteProfileBar label="Value Rating" value={profile.value} color="#22c55e" />

          {/* Meta */}
          <div className="mt-3 space-y-1.5 text-xs text-white/50">
            <div className="flex items-center gap-2">
              <MapPin size={11} className="text-crimson flex-shrink-0" />
              <span>{rec.estimated_cost}</span>
            </div>
          </div>
        </div>
      </div>
    </article>
  );
}
