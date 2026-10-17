#!/usr/bin/env node
// Browser check of the demo page: loads it at desktop and phone width, fails on console errors or
// horizontal scroll, saves screenshots + a JSON result under runs/.
// Usage: node scripts/page-check.mjs [baseUrl]   (needs playwright: npm i -D playwright, or NODE_PATH to one)
import { writeFileSync } from "node:fs";
import { chromium } from "playwright";
const BASE = (process.argv[2] || "https://c1-acute-risk.zay-259.workers.dev").replace(/\/$/, "");
const browser = await chromium.launch();
const out = { at: new Date().toISOString(), base: BASE, views: [] };
for (const [name, w, h] of [["desktop", 1280, 900], ["phone", 390, 844]]) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  const errors = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(BASE + "/demo.html", { waitUntil: "networkidle" });
  await page.waitForSelector(".kpi");
  await page.waitForSelector("#panelBody .ev");
  const hscroll = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  const rosterItems = await page.locator(".roster li").count();
  await page.screenshot({ path: `runs/demo-page-${name}.png`, fullPage: name === "desktop" });
  out.views.push({ name, width: w, errors, horizontalScroll: hscroll, rosterItems, ok: !errors.length && !hscroll && rosterItems > 0 });
  await page.close();
}
await browser.close();
writeFileSync("runs/page-check-latest.json", JSON.stringify(out, null, 1));
console.log(JSON.stringify(out.views));
process.exit(out.views.every((v) => v.ok) ? 0 : 1);
