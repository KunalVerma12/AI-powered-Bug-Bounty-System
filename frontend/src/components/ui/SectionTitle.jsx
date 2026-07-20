export function SectionTitle({ eyebrow, title, description, action }) {
  return (
    <div className="flex items-end justify-between gap-4">
      <div className="min-w-0">
        {eyebrow ? <p className="mb-2 text-xs font-bold uppercase tracking-[0.25em] text-indigo-300">{eyebrow}</p> : null}
        <h2 className="max-w-[20ch] text-balance font-display text-[clamp(1.55rem,3vw,2rem)] font-bold leading-tight tracking-tight text-white sm:max-w-none">{title}</h2>
        {description ? <p className="mt-2 max-w-[68ch] text-sm leading-6 text-slate-300">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}
