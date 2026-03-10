import Link from "next/link";

import { navigation, socialLinks, siteConfig } from "@/data/site";

import { NavLink } from "./nav-link";
import { ThemeToggle } from "./theme-toggle";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 pt-4">
      <div className="container-shell">
        <div className="glass-panel flex flex-col gap-4 rounded-[28px] px-5 py-4 sm:px-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <Link href="/" className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[color:var(--foreground)] text-sm font-semibold text-[color:var(--background)] shadow-[var(--shadow-soft)]">
                SC
              </div>
              <div className="space-y-1">
                <p className="text-base font-semibold tracking-[-0.03em] text-[color:var(--foreground)]">
                  {siteConfig.name} / {siteConfig.nameZh}
                </p>
                <p className="text-sm text-[color:var(--muted)]">
                  {siteConfig.role} · {siteConfig.subtitle}
                </p>
              </div>
            </Link>

            <div className="flex flex-col gap-3 lg:items-end">
              <nav className="flex flex-wrap gap-2">
                {navigation.map((item) => (
                  <NavLink key={item.href} href={item.href} label={item.label} />
                ))}
              </nav>

              <div className="flex flex-wrap items-center gap-3">
                <a
                  href={socialLinks[0].href}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-full border border-[color:var(--border)] px-4 py-2 text-sm text-[color:var(--foreground)] transition hover:-translate-y-0.5 hover:bg-[color:var(--surface-elevated)]"
                >
                  {socialLinks[0].label}
                </a>
                <ThemeToggle />
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
