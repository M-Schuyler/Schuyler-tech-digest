import Link from "next/link";

import type { BlogPost } from "@/data/site";
import { formatDate } from "@/lib/format-date";

type NoteCardProps = {
  post: BlogPost;
};

export function NoteCard({ post }: NoteCardProps) {
  return (
    <Link href={`/blog/${post.slug}`} className="group block h-full">
      <article className="flex h-full flex-col rounded-[30px] border border-[color:var(--border)] bg-[color:var(--surface)] p-6 shadow-[var(--shadow-card)] transition duration-300 hover:-translate-y-1.5 hover:shadow-[var(--shadow-soft)]">
        <div className="flex items-center justify-between gap-4">
          <span className="rounded-full bg-[color:var(--surface-elevated)] px-3 py-1 font-mono text-xs uppercase tracking-[0.24em] text-[color:var(--accent)]">
            {post.coverLabel}
          </span>
          <span className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]">
            {post.category}
          </span>
        </div>

        <div className="mt-5 space-y-3">
          <p className="text-xs uppercase tracking-[0.24em] text-[color:var(--muted)]">
            {formatDate(post.date)} · {post.readTime}
          </p>
          <h3 className="text-2xl font-semibold tracking-[-0.04em] text-[color:var(--foreground)]">
            {post.title}
          </h3>
          <p className="text-sm font-medium text-[color:var(--accent)]">
            {post.titleZh}
          </p>
          <p className="text-sm leading-7 text-[color:var(--muted)]">
            {post.excerpt}
          </p>
          <p className="text-sm leading-7 text-[color:var(--muted)]">
            {post.excerptZh}
          </p>
        </div>

        <div className="mt-auto pt-6 text-sm font-medium text-[color:var(--foreground)]">
          Read note
        </div>
      </article>
    </Link>
  );
}
