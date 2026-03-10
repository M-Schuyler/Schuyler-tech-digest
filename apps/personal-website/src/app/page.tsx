import Link from "next/link";

import { NoteCard } from "@/components/note-card";
import { ProjectCard } from "@/components/project-card";
import { SectionHeading } from "@/components/section-heading";
import { blogPosts, homeHighlights, projects, siteConfig, socialLinks } from "@/data/site";

const featuredProjects = projects.slice(0, 2);
const latestNotes = blogPosts.slice(0, 2);

export default function HomePage() {
  return (
    <main className="pb-20 pt-8 sm:pt-10">
      <section className="container-shell">
        <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="glass-panel rounded-[40px] px-6 py-8 sm:px-8 sm:py-10">
            <div className="inline-flex rounded-full bg-[color:var(--accent-soft)] px-4 py-2 font-mono text-xs uppercase tracking-[0.28em] text-[color:var(--accent)]">
              Automation · Robotics · Product Taste
            </div>

            <div className="mt-8 max-w-3xl space-y-6">
              <h1 className="text-4xl font-semibold tracking-[-0.07em] text-[color:var(--foreground)] sm:text-5xl lg:text-7xl">
                {siteConfig.heroTitle}
              </h1>
              <p className="text-lg font-medium tracking-[-0.03em] text-[color:var(--accent)] sm:text-2xl">
                {siteConfig.heroTitleZh}
              </p>
              <p className="max-w-2xl text-lg leading-9 text-[color:var(--muted)]">
                {siteConfig.bio}
              </p>
              <p className="max-w-2xl text-base leading-8 text-[color:var(--muted)]">
                {siteConfig.bioZh}
              </p>
            </div>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/projects"
                className="rounded-full bg-[color:var(--foreground)] px-5 py-3 text-sm font-medium text-[color:var(--background)] shadow-[var(--shadow-soft)]"
              >
                View Projects
              </Link>
              <Link
                href="/blog"
                className="rounded-full border border-[color:var(--border)] px-5 py-3 text-sm font-medium text-[color:var(--foreground)] hover:bg-[color:var(--surface-elevated)]"
              >
                Read Notes
              </Link>
              <a
                href={socialLinks[0].href}
                target="_blank"
                rel="noreferrer"
                className="rounded-full border border-[color:var(--border)] px-5 py-3 text-sm font-medium text-[color:var(--foreground)] hover:bg-[color:var(--surface-elevated)]"
              >
                GitHub
              </a>
            </div>

            <div className="mt-10 grid gap-4 md:grid-cols-4">
              {homeHighlights.map((item) => (
                <div
                  key={item.title}
                  className="rounded-[28px] border border-[color:var(--border)] bg-[color:var(--surface-elevated)] p-5"
                >
                  <p className="text-sm font-semibold text-[color:var(--foreground)]">
                    {item.title}
                  </p>
                  <p className="mt-1 text-sm text-[color:var(--accent)]">
                    {item.titleZh}
                  </p>
                  <p className="mt-3 text-sm leading-7 text-[color:var(--muted)]">
                    {item.description}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <aside className="glass-panel relative overflow-hidden rounded-[40px] px-6 py-8 sm:px-8">
            <div className="absolute right-0 top-0 h-48 w-48 rounded-full bg-[color:var(--accent-soft)] blur-3xl" />
            <div className="absolute bottom-0 left-0 h-40 w-40 rounded-full bg-[rgba(120,185,255,0.14)] blur-3xl" />
            <div className="relative space-y-8">
              <div className="space-y-4">
                <p className="font-mono text-xs uppercase tracking-[0.3em] text-[color:var(--accent)]">
                  Visual Direction / 视觉方向
                </p>
                <h2 className="text-2xl font-semibold tracking-[-0.05em] text-[color:var(--foreground)]">
                  Minimal, soft, and product-page driven.
                </h2>
                <p className="text-sm leading-7 text-[color:var(--muted)]">
                  我希望网站像作品介绍页一样，留白克制、层次清楚、颜色不吵闹，但仍然有辨识度。
                </p>
              </div>

              <div className="grid grid-cols-4 gap-3">
                {[
                  { name: "Ice", color: "bg-[#EAF3FF]" },
                  { name: "Mist", color: "bg-[#D7E7F7]" },
                  { name: "Sky", color: "bg-[#8BB8E8]" },
                  { name: "Ink", color: "bg-[#1E2A3A]" },
                ].map((item) => (
                  <div
                    key={item.name}
                    className="rounded-[24px] border border-[color:var(--border)] bg-[color:var(--surface-elevated)] p-3"
                  >
                    <div className={`h-16 rounded-[18px] ${item.color}`} />
                    <p className="mt-3 text-xs font-medium uppercase tracking-[0.18em] text-[color:var(--muted)]">
                      {item.name}
                    </p>
                  </div>
                ))}
              </div>

              <div className="grid gap-4">
                {[
                  "Robotics competition prototyping with cleaner presentation.",
                  "Bilingual writing that can live on both a website and a public account.",
                  "A long-term study of layout rhythm, color pairing, and product storytelling.",
                ].map((item) => (
                  <div
                    key={item}
                    className="rounded-[24px] border border-[color:var(--border)] bg-[color:var(--surface-elevated)] p-4 text-sm leading-7 text-[color:var(--muted)]"
                  >
                    {item}
                  </div>
                ))}
              </div>

              <div className="rounded-[28px] border border-[color:var(--border)] bg-[color:var(--surface-elevated)] p-5">
                <p className="text-sm font-semibold text-[color:var(--foreground)]">
                  Social / 社交平台
                </p>
                <div className="mt-4 grid gap-3">
                  {socialLinks.map((link) => (
                    <a
                      key={link.label}
                      href={link.href}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center justify-between rounded-2xl border border-[color:var(--border)] px-4 py-3 text-sm text-[color:var(--foreground)] hover:bg-[color:var(--background)]"
                    >
                      <span>{link.label}</span>
                      <span className="text-[color:var(--muted)]">Open</span>
                    </a>
                  ))}
                </div>
              </div>
            </div>
          </aside>
        </div>
      </section>

      <section className="container-shell mt-20 space-y-8">
        <SectionHeading
          eyebrow="Selected Work / 项目精选"
          title="Portfolio cards designed like small product stories."
          description="The project area is structured to feel closer to a clean launch page: strong titles, controlled color, and enough breathing room for engineering work to look intentional."
        />
        <div className="grid gap-6 lg:grid-cols-2">
          {featuredProjects.map((project) => (
            <ProjectCard key={project.slug} project={project} />
          ))}
        </div>
        <div>
          <Link
            href="/projects"
            className="inline-flex rounded-full border border-[color:var(--border)] px-5 py-3 text-sm font-medium text-[color:var(--foreground)] hover:bg-[color:var(--surface-elevated)]"
          >
            Browse all projects
          </Link>
        </div>
      </section>

      <section className="container-shell mt-20 grid gap-8 lg:grid-cols-[0.82fr_1.18fr]">
        <div className="glass-panel rounded-[40px] px-6 py-8 sm:px-8">
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-[color:var(--accent)]">
            Publishing / 发布方式
          </p>
          <div className="mt-6 space-y-4">
            <h2 className="text-3xl font-semibold tracking-[-0.05em] text-[color:var(--foreground)]">
              A reading space for notes, public account sync, and aesthetic
              practice.
            </h2>
            <p className="text-base leading-8 text-[color:var(--muted)]">
              The blog is not just for content dumping. It is also a place to
              practice explanation, refine visual hierarchy, and slowly build a
              more mature personal taste.
            </p>
            <p className="text-base leading-8 text-[color:var(--muted)]">
              这里不仅可以同步公众号和发布笔记，也可以作为审美训练场，去练习排版、色彩和节奏。
            </p>
          </div>
        </div>

        <div className="space-y-8">
          <SectionHeading
            eyebrow="Latest Notes / 最新笔记"
            title="Reading-first note cards with room for bilingual summaries."
            description="Use these placeholders for articles, reposted public account content, study notes, or PKM essays."
          />
          <div className="grid gap-6 lg:grid-cols-2">
            {latestNotes.map((post) => (
              <NoteCard key={post.slug} post={post} />
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
