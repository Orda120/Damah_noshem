import { clsx } from "clsx";

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={clsx(
        "w-full rounded-2xl border border-stone-300 bg-white px-4 py-3 text-sm outline-none ring-0 transition focus:border-accent",
        props.className,
      )}
    />
  );
}
