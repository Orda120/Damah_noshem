import { clsx } from "clsx";

export function Card({
  className,
  children,
}: Readonly<{ className?: string; children: React.ReactNode }>) {
  return <section className={clsx("rounded-[24px] bg-white/80 p-5 shadow-card backdrop-blur", className)}>{children}</section>;
}
