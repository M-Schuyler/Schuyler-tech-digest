import Link from "next/link";

export default function NotFound() {
  return (
    <main className="pb-20 pt-8 sm:pt-10">
      <section className="container-shell">
        <div className="glass-panel rounded-[36px] px-6 py-12 text-center sm:px-8">
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-[color:var(--accent)]">
            404
          </p>
          <h1 className="mt-4 text-4xl font-semibold tracking-[-0.06em] text-[color:var(--foreground)]">
            Page not found
          </h1>
          <p className="mt-4 text-base leading-8 text-[color:var(--muted)]">
            The page you requested is not available yet. 这个页面暂时不存在，
            你可以先回到首页继续浏览。
          </p>
          <Link
            href="/"
            className="mt-8 inline-flex rounded-full bg-[color:var(--foreground)] px-5 py-3 text-sm font-medium text-[color:var(--background)] shadow-[var(--shadow-soft)]"
          >
            Back home
          </Link>
        </div>
      </section>
    </main>
  );
}
