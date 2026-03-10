import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { blogPosts } from "@/data/site";
import { formatDate } from "@/lib/format-date";

type BlogPostPageProps = {
  params: Promise<{
    slug: string;
  }>;
};

export function generateStaticParams() {
  return blogPosts.map((post) => ({
    slug: post.slug,
  }));
}

export async function generateMetadata({
  params,
}: BlogPostPageProps): Promise<Metadata> {
  const { slug } = await params;
  const post = blogPosts.find((item) => item.slug === slug);

  if (!post) {
    return {
      title: "Note not found",
    };
  }

  return {
    title: post.title,
    description: post.excerpt,
    alternates: {
      canonical: `/blog/${post.slug}`,
    },
  };
}

export default async function BlogPostPage({ params }: BlogPostPageProps) {
  const { slug } = await params;
  const post = blogPosts.find((item) => item.slug === slug);

  if (!post) {
    notFound();
  }

  const relatedPosts = blogPosts.filter((item) => item.slug !== post.slug).slice(0, 2);

  return (
    <main className="pb-20 pt-8 sm:pt-10">
      <section className="container-shell">
        <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <article className="glass-panel rounded-[36px] px-6 py-8 sm:px-10 sm:py-10">
            <div className="space-y-4">
              <Link
                href="/blog"
                className="inline-flex rounded-full border border-[color:var(--border)] px-4 py-2 text-sm text-[color:var(--foreground)] hover:bg-[color:var(--surface-elevated)]"
              >
                Back to blog
              </Link>
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-[color:var(--accent)]">
                {post.category}
              </p>
              <h1 className="text-4xl font-semibold tracking-[-0.06em] text-[color:var(--foreground)] sm:text-5xl">
                {post.title}
              </h1>
              <p className="text-lg font-medium text-[color:var(--accent)]">
                {post.titleZh}
              </p>
              <p className="max-w-3xl text-base leading-8 text-[color:var(--muted)] sm:text-lg">
                {post.excerpt}
              </p>
            </div>

            <div className="mt-12 article-content">
              {post.sections.map((section) => (
                <section key={section.heading}>
                  <div className="space-y-2">
                    <h2>{section.heading}</h2>
                    <p className="font-medium text-[color:var(--accent)]">
                      {section.headingZh}
                    </p>
                  </div>

                  {section.paragraphs.map((paragraph) => (
                    <p key={paragraph}>{paragraph}</p>
                  ))}

                  {section.bullets ? (
                    <ul>
                      {section.bullets.map((bullet) => (
                        <li key={bullet}>{bullet}</li>
                      ))}
                    </ul>
                  ) : null}
                </section>
              ))}
            </div>
          </article>

          <aside className="space-y-6">
            <div className="glass-panel rounded-[32px] px-6 py-6">
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-[color:var(--accent)]">
                Article Meta
              </p>
              <div className="mt-5 grid gap-4">
                <div className="rounded-[22px] border border-[color:var(--border)] bg-[color:var(--surface-elevated)] p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-[color:var(--muted)]">
                    Published
                  </p>
                  <p className="mt-2 text-sm font-medium text-[color:var(--foreground)]">
                    {formatDate(post.date)}
                  </p>
                </div>
                <div className="rounded-[22px] border border-[color:var(--border)] bg-[color:var(--surface-elevated)] p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-[color:var(--muted)]">
                    Reading Time
                  </p>
                  <p className="mt-2 text-sm font-medium text-[color:var(--foreground)]">
                    {post.readTime}
                  </p>
                </div>
                <div className="rounded-[22px] border border-[color:var(--border)] bg-[color:var(--surface-elevated)] p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-[color:var(--muted)]">
                    Use Case
                  </p>
                  <p className="mt-2 text-sm leading-7 text-[color:var(--muted)]">
                    Works for original notes, synced public account articles, and
                    evergreen PKM essays.
                  </p>
                </div>
              </div>
            </div>

            <div className="glass-panel rounded-[32px] px-6 py-6">
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-[color:var(--accent)]">
                Related Notes
              </p>
              <div className="mt-5 grid gap-3">
                {relatedPosts.map((item) => (
                  <Link
                    key={item.slug}
                    href={`/blog/${item.slug}`}
                    className="rounded-[22px] border border-[color:var(--border)] bg-[color:var(--surface-elevated)] p-4 transition hover:-translate-y-0.5 hover:shadow-[var(--shadow-soft)]"
                  >
                    <p className="text-sm font-semibold text-[color:var(--foreground)]">
                      {item.title}
                    </p>
                    <p className="mt-2 text-sm leading-7 text-[color:var(--muted)]">
                      {item.titleZh}
                    </p>
                  </Link>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}
