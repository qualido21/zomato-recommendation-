export const dynamic = 'force-dynamic';

import { UtensilsCrossed } from 'lucide-react';
import Navbar from '@/components/Navbar';
import AppShell from '@/components/AppShell';
import { fetchLocations, fetchCuisines, fetchHealth } from '@/lib/api';

// Parallel server-side data fetch (no waterfall)
async function getPageData() {
  try {
    const [locations, cuisines, health] = await Promise.all([
      fetchLocations(),
      fetchCuisines(),
      fetchHealth(),
    ]);
    return { locations, cuisines, llmProvider: health.llm_provider, apiOk: true };
  } catch {
    return { locations: [], cuisines: [], llmProvider: 'groq', apiOk: false };
  }
}

export default async function HomePage() {
  const { locations, cuisines, llmProvider, apiOk } = await getPageData();

  return (
    <>
      <Navbar />

      {/* Hero Banner */}
      <div className="relative pt-14">
        <div className="h-64 bg-gradient-to-br from-zinc-900 via-stone-900 to-black overflow-hidden">
          {/* Background pattern */}
          <div className="absolute inset-0 opacity-10"
            style={{
              backgroundImage: 'radial-gradient(circle at 20% 50%, #e94560 0%, transparent 50%), radial-gradient(circle at 80% 20%, #7c3aed 0%, transparent 50%)',
            }}
          />
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-[10px] font-bold tracking-widest text-crimson/80 uppercase border border-crimson/30 px-3 py-1 rounded-full bg-crimson/10">
                AI Powered
              </span>
              <span className="text-[10px] font-bold tracking-widest text-purple-400/80 uppercase border border-purple-500/30 px-3 py-1 rounded-full bg-purple-900/10">
                Groq LLM
              </span>
            </div>
            <h1 className="font-serif text-4xl md:text-5xl font-bold text-white mb-2 leading-tight">
              Find Your Perfect<br />
              <span className="text-crimson">Bangalore</span> Restaurant
            </h1>
            <p className="text-white/40 text-sm max-w-md">
              Personalized recommendations powered by AI · {locations.length > 0 ? `${locations.length} localities` : 'Bangalore dataset'}
            </p>
          </div>
        </div>
      </div>

      {/* API offline warning */}
      {!apiOk && (
        <div className="max-w-7xl mx-auto px-6 mt-4">
          <div className="bg-red-900/20 border border-red-500/30 rounded-xl px-4 py-3 flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-red-400" />
            <div>
              <p className="text-red-400 text-sm font-semibold">Backend not reachable</p>
              <p className="text-red-400/60 text-xs mt-0.5">
                Start the API first:{' '}
                <code className="bg-red-900/30 px-1.5 py-0.5 rounded text-red-300 font-mono text-xs">
                  uvicorn src.api.main:app --reload --port 8000
                </code>
              </p>
            </div>
          </div>
        </div>
      )}

      {apiOk ? (
        <AppShell locations={locations} cuisines={cuisines} llmProvider={llmProvider} />
      ) : (
        <div className="max-w-7xl mx-auto px-6 py-16 text-center">
          <UtensilsCrossed size={40} className="text-white/10 mx-auto mb-4" />
          <p className="text-white/30 text-sm">Start the FastAPI backend to begin exploring restaurants.</p>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-white/5 mt-16 py-10">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <UtensilsCrossed size={16} className="text-crimson" />
            <span className="font-serif text-sm font-bold text-crimson">Culinary Editorial</span>
          </div>
          <div className="flex gap-8 text-xs text-white/30">
            <div>
              <p className="text-white/50 font-semibold mb-2">Platform</p>
              <p>Home</p>
              <p>Explore</p>
              <p>Favorites</p>
            </div>
            <div>
              <p className="text-white/50 font-semibold mb-2">Support</p>
              <p>About</p>
              <p>Contact</p>
              <p>FAQ</p>
            </div>
          </div>
          <p className="text-white/20 text-xs text-center md:text-right">
            Powered by Groq LLM + Zomato dataset<br />
            © 2026 Culinary Editorial
          </p>
        </div>
      </footer>
    </>
  );
}
