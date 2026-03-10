import type { Metadata } from "next";

import { ProjectCard } from "@/components/project-card";
import { SectionHeading } from "@/components/section-heading";
import { projects } from "@/data/site";

export const metadata: Metadata = {
  title: "Projects",
  description:
    "Robotics competition entries, automation prototypes, and hackathon work.",
};

export default function ProjectsPage() {
  return (
    <main className="pb-20 pt-8 sm:pt-10">
      <section className="container-shell">
        <div className="glass-panel rounded-[36px] px-6 py-8 sm:px-8 sm:py-10">
          <SectionHeading
            eyebrow="Projects / 项目"
            title="A flexible portfolio grid for robotics competitions, hackathon wins, and lab prototypes."
            description="Each card currently uses a styled visual placeholder so the site is deployable immediately. Replace those placeholders with renders, photos, or demo stills when your final assets are ready."
          />

          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {[
              "Robotics competition narratives with stronger demo framing.",
              "Hackathon projects presented as concise product cases.",
              "Experiment cards that can grow into full case studies later.",
            ].map((item) => (
              <div
                key={item}
                className="rounded-[24px] border border-[color:var(--border)] bg-[color:var(--surface-elevated)] p-5 text-sm leading-7 text-[color:var(--muted)]"
              >
                {item}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="container-shell mt-12">
        <div className="grid gap-6 lg:grid-cols-2">
          {projects.map((project) => (
            <ProjectCard key={project.slug} project={project} />
          ))}
        </div>
      </section>
    </main>
  );
}
