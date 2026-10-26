#!/usr/bin/env node

const API_BASE = "https://www.getonbrd.com/api/v0/search/jobs";

function stripHtml(html: string | null | undefined): string {
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
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

interface GetOnBrdJob {
  id: string;
  title: string;
  company: string;
  countries: string[];
  remote: boolean;
  remote_modality: string | null;
  remote_zone: string | null;
  seniority: string;
  modality: string;
  min_salary_usd: number | null;
  max_salary_usd: number | null;
  applications_count: number;
  published_at: string;
  tags: string[];
  url: string;
  description?: string;
  functions?: string;
  projects?: string;
  desirable?: string;
  benefits?: string;
}

function mapJob(item: any, includeFullText = false): GetOnBrdJob {
  const attr = item.attributes ?? {};
  const companyName =
    attr.company?.data?.attributes?.name ??
    attr.company?.data?.id ??
    "Unknown";
  const seniorityName =
    attr.seniority?.data?.attributes?.name ??
    attr.seniority?.data?.attributes?.locale_key ??
    "Unknown";
  const modalityName =
    attr.modality?.data?.attributes?.name ??
    "Full time";
  const tags: string[] = Array.isArray(attr.tags?.data)
    ? attr.tags.data
        .map((t: any) => t?.attributes?.name ?? t?.id)
        .filter(Boolean)
    : [];

  const publishedDate = attr.published_at
    ? new Date(attr.published_at * 1000).toISOString().slice(0, 10)
    : "";

  const base: GetOnBrdJob = {
    id: item.id,
    title: attr.title ?? "",
    company: companyName,
    countries: Array.isArray(attr.countries) ? attr.countries : [],
    remote: Boolean(attr.remote),
    remote_modality: attr.remote_modality ?? null,
    remote_zone: attr.remote_zone ?? null,
    seniority: seniorityName,
    modality: modalityName,
    min_salary_usd: attr.min_salary ?? null,
    max_salary_usd: attr.max_salary ?? null,
    applications_count: attr.applications_count ?? 0,
    published_at: publishedDate,
    tags,
    url: item.links?.public_url ?? `https://www.getonbrd.com/jobs/${item.id}`,
  };

  if (includeFullText) {
    base.projects = stripHtml(attr.projects);
    base.functions = stripHtml(attr.functions);
    base.description = stripHtml(attr.description);
    base.desirable = stripHtml(attr.desirable);
    base.benefits = stripHtml(attr.benefits);
  }

  return base;
}

async function fetchJobs(query: string, perPage: number, page: number): Promise<any[]> {
  const url = new URL(API_BASE);
  url.searchParams.set("query", query);
  url.searchParams.set("per_page", String(perPage));
  url.searchParams.set("page", String(page));
  url.searchParams.set("expand", JSON.stringify(["company", "modality", "seniority", "tags"]));

  const res = await fetch(url.toString(), {
    headers: {
      Accept: "application/json",
      "User-Agent": "Mozilla/5.0 (compatible; JobSearchCLI/1.0)",
    },
  });

  if (!res.ok) {
    throw new Error(`Get on Board API HTTP ${res.status}`);
  }

  const json: any = await res.json();
  return Array.isArray(json.data) ? json.data : [];
}

function renderTable(jobs: GetOnBrdJob[]): string {
  if (jobs.length === 0) return "No results.";
  const header =
    "ID".padEnd(34) +
    " " +
    "TITLE".padEnd(34) +
    " " +
    "COMPANY".padEnd(20) +
    " " +
    "SENIORITY".padEnd(12) +
    " " +
    "SALARY (USD)".padEnd(14) +
    " DATE";
  const rows = jobs.map((j) => {
    const id = (j.id || "").slice(0, 34).padEnd(34);
    const title = (j.title || "").slice(0, 34).padEnd(34);
    const company = (j.company || "—").slice(0, 20).padEnd(20);
    const sen = (j.seniority || "—").slice(0, 12).padEnd(12);
    const sal =
      j.min_salary_usd || j.max_salary_usd
        ? `$${j.min_salary_usd ?? "?"}-$${j.max_salary_usd ?? "?"}`.slice(0, 14).padEnd(14)
        : "—".padEnd(14);
    const date = j.published_at || "—";
    return `${id} ${title} ${company} ${sen} ${sal} ${date}`;
  });
  return [header, "-".repeat(header.length), ...rows].join("\n");
}

function renderPlain(jobs: GetOnBrdJob[]): string {
  if (jobs.length === 0) return "No results.";
  return jobs
    .map((j) => {
      const sal =
        j.min_salary_usd || j.max_salary_usd
          ? `$${j.min_salary_usd ?? "?"}–$${j.max_salary_usd ?? "?"} USD`
          : "Salary hidden";
      return `${j.title}\n  ${j.company} · ${j.seniority} · ${sal} · ${j.published_at || "—"}\n  id: ${j.id}\n  ${j.url}`;
    })
    .join("\n\n");
}

async function main() {
  const args = process.argv.slice(2);
  const cmd = args[0];

  if (!cmd || cmd === "--help" || cmd === "-h" || args.includes("--help") || args.includes("-h")) {
    console.log(
      "Usage:\n" +
        "  cli.ts search [query] [-q|--query <query>] [--remote] [--country <name>] [--seniority <level>] [--per-page <n>] [--page <n>] [-n|--limit <n>] [--format json|table|plain]\n" +
        "  cli.ts detail <job-id> [--query <hint>] [--format json|plain]"
    );
    process.exit(0);
  }

  if (cmd === "search") {
    let query = "";
    let onlyRemote = false;
    let countryFilter = "";
    let seniorityFilter = "";
    let perPage = 30;
    let page = 1;
    let limit = 0;
    let format: "json" | "table" | "plain" = "json";

    for (let i = 1; i < args.length; i++) {
      const a = args[i];
      if ((a === "-q" || a === "--query") && args[i + 1] !== undefined) {
        query = args[++i];
      } else if (a === "--remote") {
        onlyRemote = true;
      } else if (a === "--country" && args[i + 1] !== undefined) {
        countryFilter = args[++i].toLowerCase();
      } else if (a === "--seniority" && args[i + 1] !== undefined) {
        seniorityFilter = args[++i].toLowerCase();
      } else if (a === "--per-page" && args[i + 1] !== undefined) {
        perPage = Number(args[++i]) || 30;
      } else if (a === "--page" && args[i + 1] !== undefined) {
        page = Number(args[++i]) || 1;
      } else if ((a === "-n" || a === "--limit") && args[i + 1] !== undefined) {
        limit = Number(args[++i]) || 0;
      } else if (a === "--format" && args[i + 1] !== undefined) {
        const f = args[++i];
        if (f === "json" || f === "table" || f === "plain") format = f;
      } else if (!a.startsWith("-") && !query) {
        query = a;
      }
    }
    if (!query) query = "typescript";

    const rawItems = await fetchJobs(query, perPage, page);
    let jobs = rawItems.map((item) => mapJob(item, false));

    if (onlyRemote) {
      jobs = jobs.filter(
        (j) =>
          j.remote ||
          j.remote_modality === "fully_remote" ||
          j.remote_modality === "remote_local" ||
          j.countries.some((c) => c.toLowerCase().includes("remote"))
      );
    }

    if (countryFilter) {
      jobs = jobs.filter(
        (j) =>
          j.countries.some((c) => c.toLowerCase().includes(countryFilter)) ||
          (j.remote && j.remote_modality === "fully_remote")
      );
    }

    if (seniorityFilter) {
      jobs = jobs.filter((j) => j.seniority.toLowerCase().includes(seniorityFilter));
    }

    if (limit > 0) {
      jobs = jobs.slice(0, limit);
    }

    if (format === "table") {
      console.log(renderTable(jobs));
    } else if (format === "plain") {
      console.log(renderPlain(jobs));
    } else {
      console.log(
        JSON.stringify(
          {
            query,
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
    let jobId = "";
    let queryHint = "";
    let format: "json" | "plain" = "json";
    for (let i = 1; i < args.length; i++) {
      const a = args[i];
      if ((a === "--query" || a === "-q") && args[i + 1] !== undefined) {
        queryHint = args[++i];
      } else if (a === "--format" && args[i + 1] !== undefined) {
        const f = args[++i];
        if (f === "json" || f === "plain") format = f;
      } else if (!a.startsWith("-") && !jobId) {
        jobId = a;
      }
    }
    if (!jobId) {
      console.error("Missing <job-id>");
      process.exit(1);
    }
    if (!queryHint) {
      queryHint = jobId.replace(/-/g, " ");
    }

    const rawItems = await fetchJobs(queryHint, 50, 1);
    const match = rawItems.find((item) => item.id === jobId);
    if (!match) {
      console.log(
        JSON.stringify(
          {
            error: `Job '${jobId}' not found via search query '${queryHint}'. Try passing --query <keyword>`,
            url: `https://www.getonbrd.com/jobs/${jobId}`,
          },
          null,
          2
        )
      );
      process.exit(1);
    }

    const mapped = mapJob(match, true);
    if (format === "plain") {
      console.log(
        [
          `${mapped.title} — ${mapped.company}`,
          `Seniority: ${mapped.seniority} · Modality: ${mapped.modality} · Published: ${mapped.published_at}`,
          mapped.min_salary_usd || mapped.max_salary_usd
            ? `Salary (USD): $${mapped.min_salary_usd ?? "?"} – $${mapped.max_salary_usd ?? "?"}`
            : "",
          mapped.tags.length ? `Tags: ${mapped.tags.join(", ")}` : "",
          "",
          mapped.description ? `Description:\n${mapped.description}` : "",
          mapped.functions ? `\nFunctions:\n${mapped.functions}` : "",
          mapped.projects ? `\nProjects:\n${mapped.projects}` : "",
          mapped.desirable ? `\nDesirable:\n${mapped.desirable}` : "",
          mapped.benefits ? `\nBenefits:\n${mapped.benefits}` : "",
          "",
          `URL: ${mapped.url}`,
        ]
          .filter(Boolean)
          .join("\n")
      );
    } else {
      console.log(JSON.stringify(mapped, null, 2));
    }
    return;
  }

  console.error(`Unknown command: ${cmd}`);
  process.exit(1);
}

main().catch((err) => {
  console.error("Error:", err.message);
  process.exit(1);
});

