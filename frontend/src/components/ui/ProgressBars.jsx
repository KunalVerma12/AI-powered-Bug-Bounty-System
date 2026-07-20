export function ProgressBars() {
  return (
    <div className="flex items-end gap-1 rounded-full border border-cyan-300/10 bg-slate-950/70 px-4 py-3">
      {[0, 1, 2, 3, 4].map((index) => (
        <span
          key={index}
          className="animate-pulsebar w-1.5 rounded-full bg-cyan-200"
          style={{
            height: `${16 + index * 6}px`,
            animationDelay: `${index * 0.15}s`
          }}
        />
      ))}
    </div>
  );
}
