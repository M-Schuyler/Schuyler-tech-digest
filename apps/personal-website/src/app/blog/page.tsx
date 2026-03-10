import type { Metadata } from "next";

import { NoteCard } from "@/components/note-card";
import { SectionHeading } from "@/components/section-heading";
import { blogPosts } from "@/data/site";

export const metadata: Metadata = {
  title: "Blog",
  description:
    "Readable notes for robotics learning, public account syncing, and personal knowledge management.",
};

export default function BlogPage() {
  return (
    <main className="pb-20 pt-8 sm:pt-10">
      <section className="container-shell">
        <div className="grid gap-8 lg:grid-cols-[0.8fr_1.2fr]">
          <div className="glass-panel rounded-[36px] px-6 py-8 sm:px-8">
            <p className="font-mono text-xs uppercase tracking-[0.3em] text-[color:var(--accent)]">
              Blog / Notes
            </p>
            <div className="mt-6 space-y-4">
              <h1 className="text-4xl font-semibold tracking-[-0.06em] text-[color:var(--foreground)]">
                Reading-first notes for articles, reposted public account
                content, and PKM insights.
              </h1>
              <p className="text-base leading-8 text-[color:var(--muted)]">
                This section is already structured like a publishable archive:
                static routes, clear summaries, and article pages that feel good
                on both desktop and mobile Safari.
              </p>
              <p className="text-base leading-8 text-[color:var(--muted)]">
                你可以在这里放原创文章、公众号同步内容、课程与比赛复盘，以及个人知识管理方法。
              </p>
            </div>

            <div className="mt-8 space-y-3">
              {[
                "Draft once, then publish across multiple channels.",
                "Keep summaries, dates, and tags consistent for searchability.",
                "Use article pages for evergreen notes worth revisiting later.",
              ].map((item) => (
                <div
                  key={item}
                  className="rounded-[22px] border border-[color:var(--border)] bg-[color:var(--surface-elevated)] px-4 py-3 text-sm leading-7 text-[color:var(--muted)]"
                >
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-8">
            <SectionHeading
              eyebrow="Archive / 归档"
              title="Sample note cards with bilingual summaries and detail pages."
              description="These placeholders are fully routable, so you can publish immediately and later replace the sample content with MDX, CMS content, or an automated sync pipeline."
            />
            <div className="grid gap-6">
              {blogPosts.map((post) => (
                <NoteCard key={post.slug} post={post} />
              ))}
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
