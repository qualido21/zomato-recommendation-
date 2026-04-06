'use client';

interface TasteProfileBarProps {
  label: string;
  value: number; // 0–100
  color?: string;
}

export default function TasteProfileBar({ label, value, color = '#e94560' }: TasteProfileBarProps) {
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs text-white/60 mb-1">
        <span>{label}</span>
        <span className="font-semibold text-white">{value}%</span>
      </div>
      <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-1000 ease-out"
          style={{ width: `${value}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}
