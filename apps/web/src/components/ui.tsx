import { cn } from "@/lib/cn";
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

export function Button({
  className,
  tone = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { tone?: "primary" | "ghost" | "danger" | "soft" }) {
  const tones = {
    primary: "bg-[var(--accent)] text-[#1c1812] hover:brightness-110",
    ghost: "bg-transparent text-[var(--text)] hover:bg-[var(--bg-soft)] border border-[var(--line)]",
    danger: "bg-[var(--danger)] text-white hover:brightness-110",
    soft: "bg-[var(--bg-soft)] text-[var(--text)] hover:bg-[var(--line)]",
  };
  return (
    <button
      className={cn(
        "inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-lg px-3 text-sm font-medium transition disabled:opacity-50",
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cn(
        "min-h-11 w-full rounded-lg border border-[var(--line)] bg-[var(--bg)] px-3 text-sm text-[var(--text)] placeholder:text-[var(--muted)]",
        props.className,
      )}
    />
  );
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm text-[var(--muted)]">{label}</span>
      {children}
      {hint ? <span className="block text-xs text-[var(--muted)]">{hint}</span> : null}
    </label>
  );
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <section className={cn("rounded-2xl border border-[var(--line)] bg-[var(--bg-elev)] p-5", className)}>
      {children}
    </section>
  );
}

export function Empty({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-[var(--line)] px-6 py-12 text-center">
      <h3 className="display text-lg">{title}</h3>
      <p className="mt-2 text-sm text-[var(--muted)]">{body}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function StatusDot({ tone, label }: { tone: "ok" | "warn" | "danger" | "neutral"; label: string }) {
  const color = { ok: "bg-[var(--ok)]", warn: "bg-[var(--warn)]", danger: "bg-[var(--danger)]", neutral: "bg-[var(--muted)]" }[tone];
  return (
    <span className="inline-flex items-center gap-2 text-sm">
      <span className={cn("h-2 w-2 rounded-full", color)} aria-hidden />
      {label}
    </span>
  );
}
