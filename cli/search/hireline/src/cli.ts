#!/usr/bin/env node

import { fileURLToPath } from "node:url";

const BASE_SEARCH_URL = "https://hireline.io/mx/empleos";

export function cleanText(html: string | undefined | null): string {
  if (!html) return "";
  return html
    .replace(/<\/(p|li|h[1-6]|div|ul|ol|br)>/gi, "\n")
    .replace(/<li>/gi, "• ")
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/[ \t]+/g, " ")
    .replace(/\n\s+/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

interface HirelineJobSummary {
  id: string;
  title: string;
  company: string;
  salary: string;
  location: string;
  employment_type: string;
  updated: string;
  summary: string;
  url: string;
}

export function parseSearchCards(html: string): HirelineJobSummary[] {
  const results: HirelineJobSummary[] = [];
  const cardRegex =
    /<a\s+href="([^"]+)"\s+class="hl-vacancy-card\s+vacancy-container"[^>]*>([\s\S]*?)<\/a>/gi;

  let match: RegExpExecArray | null;
  while ((match = cardRegex.exec(html)) !== null) {
    const url = match[1].trim();
    const inner = match[2];

    const idMatch = url.match(/\/(\d+)(?:$|\?)/);
    const id = idMatch ? idMatch[1] : url;

    const updatedMatch = inner.match(/<p\s+class="updated-text"[^>]*>([\s\S]*?)<\/p>/i);
    const titleMatch = inner.match(/<p\s+class="vacancy-title"[^>]*>([\s\S]*?)<\/p>/i);
    const subtitleMatch = inner.match(/<p\s+class="vacancy-subtitle"[^>]*>([\s\S]*?)<\/p>/i);
    const summaryMatch = inner.match(/<p\s+class="vacancy-summary"[^>]*>([\s\S]*?)<\/p>/i);
    const locMatch = inner.match(/<p\s+class="vacancy-location[^"]*"[^>]*>([\s\S]*?)<\/p>/i);

    const footerTexts = [...inner.matchAll(/<p\s+class="footer-text"[^>]*>([\s\S]*?)<\/p>/gi)].map(
      (m) => cleanText(m[1])
    );

    const rawTitle = cleanText(titleMatch?.[1]);
    let title = rawTitle;
    let company = "";
    const enIndex = rawTitle.lastIndexOf(" en ");
    if (enIndex !== -1) {
      title = rawTitle.slice(0, enIndex).trim();
      company = rawTitle.slice(enIndex + 4).trim();
    }

    results.push({
      id,
      title,
      company,
      salary: cleanText(subtitleMatch?.[1]) || "Sueldo oculto",
      location: cleanText(locMatch?.[1]),
      employment_type: footerTexts[0] || "Tiempo completo",
      updated: cleanText(updatedMatch?.[1]),
      summary: cleanText(summaryMatch?.[1]),
      url,
    });
  }

  return results;
}

async function searchHireline(
  keyword: string,
  location: string,
  dateFilter: string,
  page: number
): Promise<HirelineJobSummary[]> {
  const url = new URL(BASE_SEARCH_URL);
  if (keyword) url.searchParams.set("k", keyword);
  if (location) url.searchParams.set("l", location);
  if (dateFilter) url.searchParams.set("jd", dateFilter);
  if (page > 1) url.searchParams.set("page", String(page));

  const res = await fetch(url.toString(), {
    headers: {
      Accept: "text/html,application/xhtml+xml",
      "User-Agent":
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    },
  });

  if (!res.ok) {
    throw new Error(`Hireline HTTP ${res.status}`);
  }

  const html = await res.text();
  return parseSearchCards(html);
}

async function detailHireline(targetUrl: string) {
  const res = await fetch(targetUrl, {
    headers: {
      Accept: "text/html,application/xhtml+xml",
      "User-Agent":
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    },
  });

  if (!res.ok) {
    throw new Error(`Hireline detail HTTP ${res.status}`);
  }

  const html = await res.text();
  const h1Match = html.match(
    /<h1\s+class="text-cornflower-blue\s+text-2xl\s+font-bold\s+font-outfit"[^>]*>([\s\S]*?)<\/h1>/i
  );
  const salaryMatch = html.match(
    /<p\s+class="text-vivid-sky-blue\s+text-2xl\s+font-bold\s+font-outfit\s+mb-4"[^>]*>([\s\S]*?)<\/p>/i
  );
  const publishedMatch = html.match(
    /<p\s+class="text-sm\s+text-hl-gray-400\s+mb-0\s+md:mb-1"[^>]*>([\s\S]*?)<\/p>/i
  );
  const descMatch = html.match(
    /<div\s+class="text-sm\s+text-rich-black\s+font-normal\s+ul-disc\s+overflow-wrap"[^>]*>([\s\S]*?)<\/div>/i
  );

  const metaItems = [
    ...html.matchAll(/<p\s+class="text-slate-gray\s+text-sm\s+font-medium"[^>]*>([\s\S]*?)<\/p>/gi),
  ].map((m) => cleanText(m[1]));

  return {
    url: targetUrl,
    title_and_company: cleanText(h1Match?.[1]),
    salary: cleanText(salaryMatch?.[1]) || "Sueldo oculto",
    published: cleanText(publishedMatch?.[1]),
    metadata: metaItems,
    description: cleanText(descMatch?.[1]),
  };
}

function renderTable(jobs: HirelineJobSummary[]): string {
  if (jobs.length === 0) return "No results.";
  const header =
    "ID".padEnd(8) +
    " " +
    "TITLE".padEnd(38) +
    " " +
    "COMPANY".padEnd(22) +
    " " +
    "SALARY".padEnd(20) +
    " " +
    "LOCATION".padEnd(18) +
    " UPDATED";
  const rows = jobs.map((j) => {
    const id = (j.id || "").slice(0, 8).padEnd(8);
    const title = (j.title || "").slice(0, 38).padEnd(38);
    const company = (j.company || "—").slice(0, 22).padEnd(22);
    const salary = (j.salary || "—").slice(0, 20).padEnd(20);
    const loc = (j.location || "—").slice(0, 18).padEnd(18);
    const upd = j.updated || "—";
    return `${id} ${title} ${company} ${salary} ${loc} ${upd}`;
  });
  return [header, "-".repeat(header.length), ...rows].join("\n");
}

function renderPlain(jobs: HirelineJobSummary[]): string {
  if (jobs.length === 0) return "No results.";
  return jobs
    .map(
      (j) =>
        `${j.title}\n  ${j.company || "—"} · ${j.location || "—"} · ${j.salary} · ${j.updated || "—"}\n  id: ${j.id}\n  ${j.url}`
    )
    .join("\n\n");
}

async function main() {
  const args = process.argv.slice(2);
  const cmd = args[0];

  if (!cmd || cmd === "--help" || cmd === "-h" || args.includes("--help") || args.includes("-h")) {
    console.log(
      "Usage:\n" +
        "  cli.ts search [keyword] [-q|--query <keyword>] [-l|--location <slug>] [--date <1|2|3>] [--page <n>] [-n|--limit <n>] [--format json|table|plain]\n" +
        "  cli.ts detail <hireline-job-url> [--format json|plain]"
    );
    process.exit(0);
  }

  if (cmd === "search") {
    let keyword = "";
    let location = "";
    let dateFilter = "";
    let page = 1;
    let limit = 0;
    let format: "json" | "table" | "plain" = "json";

    for (let i = 1; i < args.length; i++) {
      const a = args[i];
      if ((a === "-q" || a === "--query") && args[i + 1] !== undefined) {
        keyword = args[++i];
      } else if ((a === "-l" || a === "--location") && args[i + 1] !== undefined) {
        location = args[++i];
      } else if (a === "--date" && args[i + 1] !== undefined) {
        dateFilter = args[++i];
      } else if (a === "--page" && args[i + 1] !== undefined) {
        page = Number(args[++i]) || 1;
      } else if ((a === "-n" || a === "--limit") && args[i + 1] !== undefined) {
        limit = Number(args[++i]) || 0;
      } else if (a === "--format" && args[i + 1] !== undefined) {
        const f = args[++i];
        if (f === "json" || f === "table" || f === "plain") format = f;
      } else if (!a.startsWith("-") && !keyword) {
        keyword = a;
      }
    }

    let jobs = await searchHireline(keyword, location, dateFilter, page);
    if (limit > 0) jobs = jobs.slice(0, limit);

    if (format === "table") {
      console.log(renderTable(jobs));
    } else if (format === "plain") {
      console.log(renderPlain(jobs));
    } else {
      console.log(
        JSON.stringify(
          {
            keyword,
            location: location || "Todo México",
            page,
            total_returned: jobs.length,
            jobs,
          },
          null,
          2
        )
      );
    }
    return;
  }

  if (cmd === "detail") {
    let url = "";
    let format: "json" | "plain" = "json";
    for (let i = 1; i < args.length; i++) {
      const a = args[i];
      if (a === "--format" && args[i + 1] !== undefined) {
        const f = args[++i];
        if (f === "json" || f === "plain") format = f;
      } else if (!a.startsWith("-") && !url) {
        url = a;
      }
    }
    if (!url || !url.startsWith("http")) {
      console.error("Provide the full Hireline job URL starting with https://hireline.io/...");
      process.exit(1);
    }
    const detail = await detailHireline(url);
    if (format === "plain") {
      console.log(
        [
          detail.title_and_company,
          `Salary: ${detail.salary}`,
          detail.published ? `Published: ${detail.published}` : "",
          detail.metadata.length ? `Metadata: ${detail.metadata.join(" · ")}` : "",
          "",
          detail.description || "(no description)",
          "",
          `URL: ${detail.url}`,
        ]
          .filter(Boolean)
          .join("\n")
      );
    } else {
      console.log(JSON.stringify(detail, null, 2));
    }
    return;
  }

  console.error(`Unknown command: ${cmd}`);
  process.exit(1);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main().catch((err) => {
    console.error("Error:", err.message);
    process.exit(1);
  });
}
