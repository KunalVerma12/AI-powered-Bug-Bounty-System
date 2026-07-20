import { cn, severityTone } from "../../lib/utils";

export function SeverityBadge({ severity, className = "" }) {
  return (
    <span className={cn("inline-flex items-center rounded-full border px-3 py-1 text-xs font-bold", severityTone(severity), className)}>
      {severity}
    </span>
  );
}
