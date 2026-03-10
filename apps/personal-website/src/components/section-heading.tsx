type SectionHeadingProps = {
  eyebrow: string;
  title: string;
  description: string;
};

export function SectionHeading({
  eyebrow,
  title,
  description,
}: SectionHeadingProps) {
  return (
    <div className="space-y-4">
      <p className="font-mono text-xs uppercase tracking-[0.32em] text-[color:var(--accent)]">
        {eyebrow}
      </p>
      <div className="space-y-3">
        <h2 className="max-w-2xl text-3xl font-semibold tracking-[-0.04em] text-[color:var(--foreground)] sm:text-4xl">
          {title}
        </h2>
        <p className="max-w-2xl text-base leading-8 text-[color:var(--muted)] sm:text-lg">
          {description}
        </p>
      </div>
    </div>
  );
}
