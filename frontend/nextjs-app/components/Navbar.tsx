import Link from 'next/link';
import { Search, User, UtensilsCrossed } from 'lucide-react';

export default function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0f0f0f]/90 backdrop-blur-sm border-b border-white/5">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2 group">
          <UtensilsCrossed size={18} className="text-crimson" />
          <span className="font-serif text-base font-bold tracking-wide text-crimson group-hover:opacity-80 transition-opacity">
            Culinary Editorial
          </span>
        </Link>

        {/* Links */}
        <div className="hidden md:flex items-center gap-8 text-sm text-white/60">
          <Link href="/" className="hover:text-white transition-colors">Explore</Link>
          <span className="opacity-30 cursor-default">Favorites</span>
          <span className="opacity-30 cursor-default">Orders</span>
        </div>

        {/* Right */}
        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-2 bg-white/5 border border-white/10 rounded-full px-3 py-1.5 text-sm text-white/40">
            <Search size={13} />
            <span>Search anything...</span>
          </div>
          <div className="w-8 h-8 rounded-full bg-crimson/20 border border-crimson/30 flex items-center justify-center">
            <User size={15} className="text-crimson" />
          </div>
        </div>
      </div>
    </nav>
  );
}
