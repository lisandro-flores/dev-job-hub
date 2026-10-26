import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { parseSearchCards } from "../cli/search/hireline/src/cli.ts";
import { parseJobCards } from "../cli/search/linkedin/src/helpers.ts";
import { normalizeId } from "../cli/search/linkedin/src/commands/detail.ts";

const fixture = (name) => fs.readFileSync(new URL(`./${name}`, import.meta.url), "utf8");

test("Hireline parser maps a search card", () => {
  const [job] = parseSearchCards(fixture("hireline.fixture.html"));
  assert.equal(job.id, "123");
  assert.equal(job.title, "Frontend React Engineer");
  assert.equal(job.company, "Acme");
  assert.equal(job.location, "Remoto");
});

test("LinkedIn parser maps a job card", () => {
  const [job] = parseJobCards(fixture("linkedin.fixture.html"));
  assert.equal(job.id, "123456789");
  assert.equal(job.title, "Senior Developer");
  assert.equal(job.company, "Acme");
  assert.equal(job.date, "2026-10-25");
});

test("LinkedIn detail rejects look-alike hosts", () => {
  assert.equal(normalizeId("https://linkedin.com.evil.example/jobs/view/123456789"), null);
  assert.equal(normalizeId("https://www.linkedin.com/jobs/view/senior-developer-123456789"), "123456789");
});
