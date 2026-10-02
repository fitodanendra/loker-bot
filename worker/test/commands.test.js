import { test } from "node:test";
import assert from "node:assert/strict";

import { handleText, defaultPrefs } from "../src/commands.js";

const BUILTIN = ["video", "motion", "fullstack"];
const JABO = ["Jakarta", "Tangerang"];

function run(text, prefs = {}) {
  const base = { ...defaultPrefs(BUILTIN), ...prefs };
  return handleText(text, { builtin: BUILTIN, defaultLocations: JABO, prefs: base });
}

const active = (result) => [...result.prefs.active].sort();

// --- categories -----------------------------------------------------------

test("/pilih keeps only the given categories", () => {
  const result = run("/pilih fullstack");
  assert.deepEqual(active(result), ["fullstack"]);
  assert.match(result.reply, /fullstack/);
});

test("/pilih accepts several categories", () => {
  assert.deepEqual(active(run("/pilih video motion")), ["motion", "video"]);
});

test("/tambah adds and /hapus removes a category", () => {
  assert.deepEqual(active(run("/tambah motion", { active: ["video"] })), ["motion", "video"]);
  assert.deepEqual(active(run("/hapus video")), ["fullstack", "motion"]);
});

test("/hapus refuses to remove the last active category", () => {
  const result = run("/hapus video", { active: ["video"] });
  assert.deepEqual(active(result), ["video"]);
  assert.match(result.reply.toLowerCase(), /minimal satu/);
});

test("/semua activates every category including custom ones", () => {
  const result = run("/semua", { active: ["video"], custom: { "3d": "3d" } });
  assert.deepEqual(active(result), ["3d", "fullstack", "motion", "video"]);
});

test("unknown category is rejected without change", () => {
  const result = run("/pilih dokter");
  assert.deepEqual(active(result), ["fullstack", "motion", "video"]);
  assert.match(result.reply, /dokter/);
});

test("names are case-insensitive, ignore punctuation and the @bot suffix", () => {
  assert.deepEqual(active(run("/Pilih@pencarijob_bot FullStack")), ["fullstack"]);
  assert.deepEqual(active(run("/pilih full-stack")), ["fullstack"]);
});

test("/kategori lists statuses without change", () => {
  const result = run("/kategori", { active: ["video"] });
  assert.deepEqual(active(result), ["video"]);
  assert.match(result.reply, /✅ video/);
  assert.match(result.reply, /❌ motion/);
});

test("plain text shows help", () => {
  const result = run("halo");
  assert.match(result.reply, /\/pilih/);
  assert.equal(result.changed, false);
});

// --- custom categories ----------------------------------------------------

test("/baru creates and activates a custom category and lists all statuses", () => {
  const result = run("/baru Graphic Designer", { active: ["video"] });
  assert.deepEqual(result.prefs.custom, { graphicdesigner: "graphic designer" });
  assert.deepEqual(active(result), ["graphicdesigner", "video"]);
  assert.match(result.reply, /✅ video/);
  assert.match(result.reply, /❌ motion/);
  assert.match(result.reply, /✅ graphicdesigner/);
});

test("/baru rejects empty, duplicate, too long and over-limit keywords", () => {
  assert.match(run("/baru").reply, /\/baru graphic designer/);
  assert.match(run("/baru Video").reply, /sudah ada/);
  assert.deepEqual(run("/baru " + "a".repeat(61)).prefs.custom, {});
  const full = Object.fromEntries(Array.from({ length: 10 }, (_, i) => [`k${i}`, `k${i}`]));
  assert.match(run("/baru extra", { custom: full }).reply, /10/);
});

test("/buang removes a custom category by name or keyword", () => {
  const prefs = { custom: { graphicdesigner: "graphic designer" }, active: ["video", "graphicdesigner"] };
  const result = run("/buang graphic designer", prefs);
  assert.deepEqual(result.prefs.custom, {});
  assert.deepEqual(active(result), ["video"]);
});

test("/buang refuses builtin categories and reactivates all when last is removed", () => {
  assert.match(run("/buang video").reply, /\/hapus/);
  const result = run("/buang x", { custom: { x: "x" }, active: ["x"] });
  assert.deepEqual(active(result), ["fullstack", "motion", "video"]);
});

test("handleText does not mutate the input prefs", () => {
  const prefs = { ...defaultPrefs(BUILTIN), custom: { a: "a" } };
  handleText("/baru b", { builtin: BUILTIN, defaultLocations: JABO, prefs });
  assert.deepEqual(prefs.custom, { a: "a" });
});

// --- locations ------------------------------------------------------------

test("/tambahlokasi starts from the default locations and title-cases", () => {
  const result = run("/tambahlokasi tangerang selatan");
  assert.deepEqual(result.prefs.locations, ["Jakarta", "Tangerang", "Tangerang Selatan"]);
});

test("/tambahlokasi ignores duplicates and starts fresh from all-Indonesia", () => {
  assert.deepEqual(run("/tambahlokasi jakarta").prefs.locations, null);
  assert.deepEqual(run("/tambahlokasi bandung", { locations: [] }).prefs.locations, ["Bandung"]);
});

test("/hapuslokasi removes, refuses last and unknown", () => {
  assert.deepEqual(run("/hapuslokasi TANGERANG").prefs.locations, ["Jakarta"]);
  assert.match(run("/hapuslokasi jakarta", { locations: ["Jakarta"] }).reply, /\/semualokasi/);
  assert.match(run("/hapuslokasi bali").reply, /Bali/);
});

test("/semualokasi means all of Indonesia; /lokasi only shows", () => {
  const all = run("/semualokasi");
  assert.deepEqual(all.prefs.locations, []);
  assert.match(all.reply, /Seluruh Indonesia/);
  const show = run("/lokasi");
  assert.equal(show.changed, false);
  assert.match(show.reply, /Jakarta/);
});
