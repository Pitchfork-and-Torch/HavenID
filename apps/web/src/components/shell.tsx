"use client";

import { Command } from "cmdk";
import { Menu, Phone, Shield, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Me } from "@/lib/api";
import { Button } from "./ui";
import { cn } from "@/lib/cn";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/calls", label: "Calls" },
  { href: "/contacts", label: "Contacts" },
  { href: "/lists", label: "Lists" },
  { href: "/devices", label: "Devices" },
  { href: "/security", label: "Security" },
  { href: "/telephony", label: "Telephony" },
  { href: "/settings", label: "Settings" },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [open, setOpen] = useState(false);
  const [cmd, setCmd] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    api<Me>("/api/v1/me")
      .then((data) => {
        setMe(data);
        document.documentElement.dataset.theme = data.prefs?.theme === "light" ? "light" : "dark";
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCmd((v) => !v);
      }
      if (e.key === "Escape") setCmd(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  async function logout() {
    await api("/api/v1/auth/logout", { method: "POST" });
    router.replace("/login");
  }

  return (
    <div className="min-h-screen md:grid md:grid-cols-[240px_1fr]">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <aside className="hidden border-r border-[var(--line)] bg-[var(--bg-elev)] md:flex md:flex-col">
        <div className="flex items-center gap-2 px-5 py-5">
          <Shield className="h-5 w-5 text-[var(--accent)]" aria-hidden />
          <span className="display text-xl tracking-tight">HavenID</span>
        </div>
        <nav className="flex flex-1 flex-col gap-0.5 px-3" aria-label="Primary">
          {NAV.map((item) => {
            const active = item.href === "/" ? path === "/" : path.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "min-h-11 rounded-lg px-3 py-2 text-sm",
                  active ? "bg-[var(--bg-soft)] text-[var(--text)]" : "text-[var(--muted)] hover:bg-[var(--bg-soft)] hover:text-[var(--text)]",
                )}
                aria-current={active ? "page" : undefined}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-[var(--line)] p-4 text-xs text-[var(--muted)]">
          <div className="truncate">{me?.email}</div>
          <button className="mt-2 min-h-11 text-left text-[var(--text)] underline-offset-2 hover:underline" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex min-h-screen flex-col">
        <header className="flex items-center justify-between border-b border-[var(--line)] px-4 py-3 md:px-8">
          <button className="min-h-11 min-w-11 md:hidden" aria-label="Open menu" onClick={() => setOpen(true)}>
            <Menu className="h-5 w-5" />
          </button>
          <div className="hidden items-center gap-2 text-sm text-[var(--muted)] md:flex">
            <Phone className="h-4 w-4" aria-hidden />
            {me?.twilio_configured ? (me.twilio_trial ? "Twilio trial" : "Twilio ready") : "Twilio not set"}
          </div>
          <Button tone="ghost" className="hidden md:inline-flex" onClick={() => setCmd(true)}>
            Search  Ctrl K
          </Button>
          <span className="display text-lg md:hidden">HavenID</span>
        </header>

        {open ? (
          <div className="fixed inset-0 z-40 bg-black/50 md:hidden" role="dialog" aria-modal="true">
            <div className="h-full w-64 bg-[var(--bg-elev)] p-4">
              <div className="mb-4 flex justify-between">
                <span className="display text-lg">HavenID</span>
                <button className="min-h-11 min-w-11" aria-label="Close menu" onClick={() => setOpen(false)}>
                  <X />
                </button>
              </div>
              <nav className="flex flex-col gap-1">
                {NAV.map((item) => (
                  <Link key={item.href} href={item.href} className="min-h-11 px-2 py-2" onClick={() => setOpen(false)}>
                    {item.label}
                  </Link>
                ))}
              </nav>
            </div>
          </div>
        ) : null}

        {cmd ? (
          <div className="fixed inset-0 z-50 bg-black/50 p-4" onClick={() => setCmd(false)}>
            <Command
              className="mx-auto mt-24 max-w-lg overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--bg-elev)]"
              onClick={(e) => e.stopPropagation()}
            >
              <Command.Input className="h-12 w-full border-b border-[var(--line)] bg-transparent px-4" placeholder="Jump to..." />
              <Command.List className="max-h-72 overflow-auto p-2">
                <Command.Empty className="px-3 py-6 text-sm text-[var(--muted)]">No matches</Command.Empty>
                <Command.Group heading="Pages">
                  {NAV.map((item) => (
                    <Command.Item
                      key={item.href}
                      onSelect={() => {
                        setCmd(false);
                        router.push(item.href);
                      }}
                      className="min-h-11 cursor-pointer rounded-md px-3 py-2 text-sm aria-selected:bg-[var(--bg-soft)]"
                    >
                      {item.label}
                    </Command.Item>
                  ))}
                </Command.Group>
              </Command.List>
            </Command>
          </div>
        ) : null}

        <main id="main" className="flex-1 px-4 py-6 md:px-8">
          {err ? <p className="mb-4 text-sm text-[var(--danger)]">{err}</p> : null}
          {me ? children : <p className="text-sm text-[var(--muted)]">Loading...</p>}
        </main>

        <nav className="sticky bottom-0 grid grid-cols-4 border-t border-[var(--line)] bg-[var(--bg-elev)] md:hidden" aria-label="Mobile">
          {[NAV[0], NAV[1], NAV[2], NAV[7]].map((item) => (
            <Link key={item.href} href={item.href} className="flex min-h-12 items-center justify-center text-xs">
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </div>
  );
}
