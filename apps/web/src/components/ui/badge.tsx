import { clsx } from "clsx";

export function Badge({
  tone = "default",
  children,
}: Readonly<{ tone?: "default" | "success" | "muted" | "danger"; children: React.ReactNode }>) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold",
        tone === "default" && "bg-accent/10 text-accent",
        tone === "success" && "bg-emerald-100 text-emerald-800",
        tone === "muted" && "bg-stone-200 text-stone-700",
        tone === "danger" && "bg-rose-100 text-rose-800",
      )}
    >
      {children}
    </span>
  );
}
