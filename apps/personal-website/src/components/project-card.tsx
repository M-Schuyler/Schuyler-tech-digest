import type { Project } from "@/data/site";

type ProjectCardProps = {
  project: Project;
};

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <article className="group flex h-full flex-col overflow-hidden rounded-[30px] border border-[color:var(--border)] bg-[color:var(--surface)] shadow-[var(--shadow-card)] transition duration-300 hover:-translate-y-1.5 hover:shadow-[var(--shadow-soft)]">
      <div
        className="relative h-56 overflow-hidden border-b border-[color:var(--border)]"
        style={{ backgroundImage: project.visual }}
      >
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.32),transparent_40%)]" />
        <div className="absolute left-6 top-6 flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-black/15 px-3 py-1 font-mono uppercase tracking-[0.2em] text-white backdrop-blur-sm">
            {project.category}
          </span>
          <span className="rounded-full bg-white/16 px-3 py-1 text-white/88 backdrop-blur-sm">
            {project.badge}
          </span>
        </div>
        <div className="absolute inset-x-6 bottom-6 space-y-1">
          <p className="text-xs uppercase tracking-[0.3em] text-white/78">
            {project.categoryZh}
          </p>
          <p className="text-3xl font-semibold tracking-[-0.04em] text-white">
            {project.titleZh}
          </p>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-4 p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <h3 className="text-xl font-semibold tracking-[-0.03em] text-[color:var(--foreground)]">
              {project.title}
            </h3>
            <p className="text-sm text-[color:var(--muted)]">{project.year}</p>
          </div>
          <span className="rounded-full border border-[color:var(--border)] px-3 py-1 text-xs text-[color:var(--muted)]">
            Placeholder
          </span>
        </div>

        <p className="text-sm leading-7 text-[color:var(--muted)]">
          {project.description}
        </p>

        <div className="mt-auto flex flex-wrap gap-2 pt-2">
          {project.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-[color:var(--surface-elevated)] px-3 py-1 text-xs text-[color:var(--muted)]"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
    </article>
  );
}
