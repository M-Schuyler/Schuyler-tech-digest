import { socialLinks, siteConfig } from "@/data/site";

export function SiteFooter() {
  return (
    <footer className="pb-10 pt-20">
      <div className="container-shell">
        <div className="glass-panel grid gap-8 rounded-[32px] px-6 py-8 sm:px-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-4">
            <p className="font-mono text-xs uppercase tracking-[0.3em] text-[color:var(--accent)]">
              Contact / 联系方式
            </p>
            <div className="space-y-3">
              <h2 className="text-2xl font-semibold tracking-[-0.04em] text-[color:var(--foreground)]">
                {siteConfig.role} · {siteConfig.subtitle}
              </h2>
              <p className="max-w-2xl text-sm leading-7 text-[color:var(--muted)]">
                {siteConfig.availability}
              </p>
              <a
                href={`mailto:${siteConfig.email}`}
                className="inline-flex rounded-full border border-[color:var(--border)] px-4 py-2 text-sm font-medium text-[color:var(--foreground)] transition hover:bg-[color:var(--surface-elevated)]"
              >
                {siteConfig.email}
              </a>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {socialLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                target="_blank"
                rel="noreferrer"
                className="rounded-[24px] border border-[color:var(--border)] bg-[color:var(--surface-elevated)] p-4 transition hover:-translate-y-1 hover:shadow-[var(--shadow-soft)]"
              >
                <p className="text-sm font-semibold text-[color:var(--foreground)]">
                  {link.label}
                </p>
                <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">
                  {link.description}
                </p>
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
