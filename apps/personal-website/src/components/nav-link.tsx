"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type NavLinkProps = {
  href: "/" | "/projects" | "/blog";
  label: string;
};

export function NavLink({ href, label }: NavLinkProps) {
  const pathname = usePathname();
  const isActive = href === "/" ? pathname === href : pathname.startsWith(href);

  return (
    <Link
      href={href}
      className={[
        "rounded-full px-4 py-2 text-sm transition",
        isActive
          ? "bg-[color:var(--foreground)] text-[color:var(--background)] shadow-[var(--shadow-soft)]"
          : "text-[color:var(--muted)] hover:bg-[color:var(--surface-elevated)] hover:text-[color:var(--foreground)]",
      ].join(" ")}
    >
      {label}
    </Link>
  );
}
