export function cn(...classes) {
  return classes.filter(Boolean).join(" ");
}

export function formatDate(value) {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

export function severityTone(severity) {
  switch (severity) {
    case "Critical":
      return "bg-rose-500/15 text-rose-100 border-rose-500/30";
    case "High":
      return "bg-orange-500/15 text-orange-100 border-orange-500/30";
    case "Medium":
      return "bg-amber-500/15 text-amber-100 border-amber-500/30";
    default:
      return "bg-emerald-500/15 text-emerald-100 border-emerald-500/30";
  }
}

export function statusTone(status) {
  if (status === "Completed") {
    return "text-emerald-300";
  }
  if (status === "Running") {
    return "text-sky-300";
  }
  if (status === "Queued") {
    return "text-violet-300";
  }
  if (status === "Failed") {
    return "text-rose-300";
  }
  return "text-slate-300";
}
