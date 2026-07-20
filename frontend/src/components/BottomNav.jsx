import { motion } from "framer-motion";
import { Activity, FolderGit2, Home, Radar, UserCircle2 } from "lucide-react";
import { cn } from "../lib/utils";

const items = [
  { id: "home", label: "Home", icon: Home },
  { id: "workspace", label: "Workspace", icon: FolderGit2 },
  { id: "scan", label: "Scan", icon: Radar },
  { id: "activity", label: "Activity", icon: Activity },
  { id: "profile", label: "Profile", icon: UserCircle2 }
];

export function BottomNav({ active, onChange }) {
  return (
    <nav className="fixed bottom-3 left-1/2 z-40 w-[calc(100%-1.5rem)] max-w-[520px] -translate-x-1/2 rounded-[20px] border border-white/10 bg-[#080c19]/90 p-1.5 shadow-[0_16px_40px_rgba(0,0,0,0.32)] backdrop-blur-2xl sm:bottom-4">
      <div className="grid grid-cols-5 gap-1">
        {items.map(({ id, label, icon: Icon }) => (
          <motion.button
            key={id}
            type="button"
            onClick={() => onChange(id)}
            whileTap={{ scale: 0.96 }}
            whileHover={{ y: -2 }}
            className={cn(
              "flex min-w-0 flex-col items-center justify-center gap-0.5 rounded-[15px] px-1.5 py-2 text-[10px] font-semibold transition sm:gap-1 sm:px-2 sm:py-2.5 sm:text-[11px]",
              active === id
                ? "bg-cyan-300 text-slate-950 shadow-[0_0_18px_rgba(34,211,238,0.18)]"
                : "text-slate-400 hover:bg-white/[0.08] hover:text-white"
            )}
          >
            <Icon size={17} />
            <span className="max-w-full truncate">{label}</span>
          </motion.button>
        ))}
      </div>
    </nav>
  );
}
