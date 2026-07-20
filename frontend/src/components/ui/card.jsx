import { cn } from "../../lib/utils";

export function Card({ className = "", children, ...props }) {
  return (
    <div className={cn("rounded-[22px] border border-white/10 bg-white/[0.055] shadow-soft backdrop-blur-xl", className)} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ className = "", children, ...props }) {
  return (
    <div className={cn("space-y-1.5 p-5", className)} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({ className = "", children, ...props }) {
  return (
    <h3 className={cn("font-display text-xl font-bold leading-tight text-white", className)} {...props}>
      {children}
    </h3>
  );
}

export function CardContent({ className = "", children, ...props }) {
  return (
    <div className={cn("p-5 pt-0", className)} {...props}>
      {children}
    </div>
  );
}
