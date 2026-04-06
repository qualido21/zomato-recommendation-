import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Culinary Editorial — AI Restaurant Recommender',
  description: 'AI-powered restaurant recommendations for Bangalore, powered by Groq LLM.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#0f0f0f] text-white antialiased">
        {children}
      </body>
    </html>
  );
}
