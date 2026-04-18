import { clsx } from "clsx";

export function Button(
  props: React.ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "primary" | "secondary" | "ghost" | "danger";
  },
) {
  const { className, variant = "primary", ...rest } = props;
  return (
    <button
      className={clsx(
        "rounded-full px-4 py-2 text-sm font-medium transition",
        variant === "primary" && "bg-accent text-white hover:bg-[#145547]",
        variant === "secondary" && "bg-sand text-ink hover:bg-[#cdbb9a]",
        variant === "ghost" && "bg-transparent text-ink hover:bg-white/50",
        variant === "danger" && "bg-alert text-white hover:bg-[#7a2323]",
        className,
      )}
      {...rest}
    />
  );
}
