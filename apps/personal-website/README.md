# Personal Website Scaffold

A bilingual personal website scaffold built with Next.js App Router, TypeScript, and Tailwind CSS. The current content positions the site owner as an Automation / Robotics student and `校园学长`, with dedicated sections for projects and long-form notes.

## Stack

- Next.js 16 (App Router)
- React 19
- Tailwind CSS 4
- TypeScript

## Included pages

- `/` home landing page
- `/projects` portfolio grid for robotics and hackathon work
- `/blog` notes index optimized for reading
- `/blog/[slug]` sample note detail pages

## Project structure

```text
src/
  app/
  components/
  data/
  lib/
```

## Local development

```bash
cd apps/personal-website
npm install
npm run dev
```

Production checks:

```bash
npm run check
npm run build
```

## Personalization

Update these files first:

- `src/data/site.ts` for profile text, project cards, blog notes, and navigation data
- `.env.local` copied from `.env.example` for social links and canonical site URL

Available environment variables:

- `NEXT_PUBLIC_SITE_URL`
- `NEXT_PUBLIC_GITHUB_URL`
- `NEXT_PUBLIC_LINKEDIN_URL`
- `NEXT_PUBLIC_X_URL`
- `NEXT_PUBLIC_WECHAT_URL`

## GitHub and Vercel

This workspace is organized into `apps/`, `services/`, and `playgrounds/`, so the website now lives in `apps/personal-website/`.

If you want the website as its own repo:

```bash
cd apps/personal-website
git init
git add .
git commit -m "Initial personal website scaffold"
```

If you deploy the current repository to Vercel, set the project Root Directory to `apps/personal-website`.

If you push `apps/personal-website/` as a standalone repo, Vercel works with the default Next.js preset. Add the environment variables above, then deploy.
