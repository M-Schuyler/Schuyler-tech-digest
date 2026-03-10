export type SocialLink = {
  label: string;
  href: string;
  description: string;
};

export type HomeHighlight = {
  title: string;
  titleZh: string;
  description: string;
};

export type Project = {
  slug: string;
  title: string;
  titleZh: string;
  year: string;
  category: string;
  categoryZh: string;
  badge: string;
  description: string;
  tags: string[];
  visual: string;
};

export type BlogSection = {
  heading: string;
  headingZh: string;
  paragraphs: string[];
  bullets?: string[];
};

export type BlogPost = {
  slug: string;
  title: string;
  titleZh: string;
  category: string;
  date: string;
  readTime: string;
  excerpt: string;
  excerptZh: string;
  coverLabel: string;
  sections: BlogSection[];
};

const siteUrl =
  process.env.NEXT_PUBLIC_SITE_URL ?? "https://your-portfolio.vercel.app";

export const siteConfig = {
  name: "Shukai Chen",
  nameZh: "陈书锴",
  role: "Automation & Robotics Student",
  roleZh: "自动化与机器人学生",
  subtitle: "Campus Senior / 校园学长",
  heroTitle: "Dreaming of experiencing the world.",
  heroTitleZh: "梦想是体验世界",
  description:
    "A bilingual personal website for robotics prototypes, hackathon work, and calm, Apple-inspired engineering notes.",
  bio: "I study automation and robotics, build practical prototypes, and document what I learn with a product-minded approach. I care about systems that feel clear, calm, and thoughtfully presented.",
  bioZh:
    "我是一名自动化与机器人方向的学生，也想用校园学长的视角记录成长、项目和审美训练。我希望把工程实践做得更清晰，把页面表达做得更克制，也持续学习像苹果产品介绍页那样的色彩搭配与信息呈现。",
  location: "Based in China",
  availability:
    "Open to research collaboration, prototype work, student mentorship, and better visual storytelling.",
  siteUrl,
  email: "cjsikecrj@gmail.com",
};

export const navigation = [
  { href: "/", label: "Home" },
  { href: "/projects", label: "Projects" },
  { href: "/blog", label: "Blog" },
] as const;

export const socialLinks: SocialLink[] = [
  {
    label: "GitHub",
    href: process.env.NEXT_PUBLIC_GITHUB_URL ?? "https://github.com/M-Schuyler",
    description: "Code, prototypes, and technical experiments.",
  },
  {
    label: "LinkedIn",
    href:
      process.env.NEXT_PUBLIC_LINKEDIN_URL ??
      "https://www.linkedin.com/in/your-handle",
    description: "Professional profile and project snapshots.",
  },
  {
    label: "X",
    href: process.env.NEXT_PUBLIC_X_URL ?? "https://x.com/your-handle",
    description: "Short-form thoughts on robotics, tools, and campus life.",
  },
  {
    label: "WeChat / 公众号",
    href: process.env.NEXT_PUBLIC_WECHAT_URL ?? "https://mp.weixin.qq.com/",
    description: "Public account posts and long-form reflections.",
  },
];

export const homeHighlights: HomeHighlight[] = [
  {
    title: "Competition-Ready",
    titleZh: "竞赛级原型",
    description:
      "From sensors and embedded control to a polished demo narrative.",
  },
  {
    title: "Bilingual Writing",
    titleZh: "双语表达",
    description:
      "Clear English for the web, clear Chinese where context matters.",
  },
  {
    title: "Visual Taste",
    titleZh: "页面审美",
    description:
      "Learning color, pacing, and hierarchy from strong product storytelling.",
  },
  {
    title: "Mentor Mindset",
    titleZh: "学长视角",
    description:
      "Practical notes for younger students navigating campus and projects.",
  },
];

export const projects: Project[] = [
  {
    slug: "smart-shoe-cabinet",
    title: "Smart Shoe Cabinet",
    titleZh: "智能鞋柜",
    year: "2025",
    category: "Robotics Competition",
    categoryZh: "机器人竞赛",
    badge: "Embedded + Vision",
    description:
      "A dorm-scale automation concept that pairs humidity sensing, RFID identification, and a compact retrieval mechanism for tidy storage and low-friction access.",
    tags: ["STM32", "Sensors", "Motor Control", "Industrial Design"],
    visual:
      "linear-gradient(135deg, rgba(10,132,255,0.88), rgba(91,197,255,0.72) 45%, rgba(244,247,251,0.18) 100%)",
  },
  {
    slug: "warehouse-rover",
    title: "Warehouse Rover",
    titleZh: "仓储巡检小车",
    year: "2024",
    category: "Autonomous Systems",
    categoryZh: "自主系统",
    badge: "Control + Navigation",
    description:
      "A line-following inspection rover built for repeatable indoor logistics demos, with obstacle handling, telemetry, and a compact mechanical frame.",
    tags: ["ROS", "Navigation", "PID", "Telemetry"],
    visual:
      "linear-gradient(135deg, rgba(15,118,110,0.9), rgba(94,234,212,0.72) 50%, rgba(244,247,251,0.14) 100%)",
  },
  {
    slug: "campus-flow-assistant",
    title: "Campus Flow Assistant",
    titleZh: "校园流程助手",
    year: "2025",
    category: "Hackathon Winner",
    categoryZh: "黑客松获奖作品",
    badge: "AI + Automation",
    description:
      "A student-facing assistant that simplifies repetitive campus tasks such as class reminders, document tracking, and deadline nudges through lightweight automation.",
    tags: ["Next.js", "LLM Workflow", "UX", "Rapid Prototyping"],
    visual:
      "linear-gradient(135deg, rgba(17,24,39,0.96), rgba(71,85,105,0.88) 45%, rgba(10,132,255,0.52) 100%)",
  },
  {
    slug: "vision-sorting-demo",
    title: "Vision Sorting Demo",
    titleZh: "视觉分拣演示",
    year: "2024",
    category: "Automation Lab",
    categoryZh: "自动化实验室",
    badge: "CV + Actuation",
    description:
      "A compact classification line that identifies object color and shape, then routes items with a camera-assisted decision loop and synchronized actuators.",
    tags: ["OpenCV", "Servo", "Python", "System Integration"],
    visual:
      "linear-gradient(135deg, rgba(245,158,11,0.92), rgba(251,191,36,0.76) 40%, rgba(15,23,42,0.18) 100%)",
  },
];

export const blogPosts: BlogPost[] = [
  {
    slug: "public-account-sync-workflow",
    title: "Public Account Sync Without Losing Readability",
    titleZh: "公众号同步，但不牺牲阅读体验",
    category: "Publishing Workflow",
    date: "2026-02-18",
    readTime: "6 min read",
    excerpt:
      "A lightweight publishing flow for turning public account posts into clean website notes with better structure, metadata, and long-term searchability.",
    excerptZh:
      "把公众号内容同步到个人网站时，我更在意结构化、可检索、长期可复用，而不是简单复制粘贴。",
    coverLabel: "SYNC",
    sections: [
      {
        heading: "Why the website matters",
        headingZh: "为什么个人网站仍然重要",
        paragraphs: [
          "A public account is great for distribution, but a personal site is better for navigation, archives, and durable identity. When notes live on the site, readers can actually browse by topic instead of digging through a feed.",
          "For engineering writing, structure matters. Headings, summaries, and consistent metadata make the difference between a one-time post and a reusable knowledge asset.",
        ],
      },
      {
        heading: "A simple workflow",
        headingZh: "一个简单可执行的流程",
        paragraphs: [
          "I draft the long-form article once, then adapt the packaging to each channel. The public account keeps the native social format, while the website version focuses on scanning, search, and clean linking.",
        ],
        bullets: [
          "Write once with headings and summary blocks already defined.",
          "Publish the social version for distribution and conversation.",
          "Republish the site version with cleaner typography and tags.",
          "Archive the final note into a searchable personal knowledge base.",
        ],
      },
    ],
  },
  {
    slug: "robotics-notes-for-juniors",
    title: "Robotics Notes for Younger Students",
    titleZh: "给机器人方向学弟学妹的笔记",
    category: "Campus Notes",
    date: "2026-01-28",
    readTime: "5 min read",
    excerpt:
      "A practical note on choosing projects, documenting work, and avoiding the trap of building flashy demos without a coherent engineering story.",
    excerptZh:
      "真正能打动老师、队友和面试官的，不只是炫酷功能，而是完整的问题定义、方案取舍和验证过程。",
    coverLabel: "GUIDE",
    sections: [
      {
        heading: "Pick projects with a narrative",
        headingZh: "选项目时先看叙事闭环",
        paragraphs: [
          "A good student project is not just a collection of modules. It has a problem statement, design constraints, a test plan, and a clear result that another person can understand in two minutes.",
          "That is why small but coherent prototypes often beat oversized concepts. A simple robot that works reliably tells a stronger story than a complex system that never stabilizes.",
        ],
      },
      {
        heading: "Document while you build",
        headingZh: "边做边记录",
        paragraphs: [
          "Keep diagrams, photos, and short engineering notes as the work happens. Waiting until the end creates weak portfolios because the real decision points are already forgotten.",
        ],
        bullets: [
          "Record each prototype change and why it happened.",
          "Capture tests, failures, and what improved after each fix.",
          "Write captions that a non-specialist reader can still follow.",
        ],
      },
    ],
  },
  {
    slug: "lightweight-pkm-for-engineering",
    title: "Lightweight PKM for Engineering Work",
    titleZh: "面向工程实践的轻量知识管理",
    category: "PKM",
    date: "2025-12-16",
    readTime: "7 min read",
    excerpt:
      "A minimal personal knowledge system for busy semesters: capture quickly, refine selectively, and only preserve notes that help future projects move faster.",
    excerptZh:
      "知识管理不应该变成额外负担，它应该像实验记录一样，服务于下一次更快、更稳地完成项目。",
    coverLabel: "PKM",
    sections: [
      {
        heading: "Collect less, connect more",
        headingZh: "少收藏，多连接",
        paragraphs: [
          "Most students over-collect and under-synthesize. A useful PKM system keeps only what is tied to current work, likely future work, or a recurring teaching note.",
          "When notes are connected to projects, talks, and articles, they become easier to reuse and much harder to abandon.",
        ],
      },
      {
        heading: "The three-layer stack",
        headingZh: "三层式知识管理",
        paragraphs: [
          "My preferred stack is intentionally small: quick capture, project notes, and polished evergreen notes. Each layer has a different speed and a different quality bar.",
        ],
        bullets: [
          "Capture: fleeting ideas, raw links, fast reminders.",
          "Project notes: active experiments, component choices, test results.",
          "Evergreen notes: refined writeups worth publishing or reusing.",
        ],
      },
    ],
  },
];
