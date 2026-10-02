import { test } from "node:test";
import assert from "node:assert/strict";

import worker from "../src/index.js";

function memoryKV(initial = {}) {
  const store = new Map(Object.entries(initial).map(([k, v]) => [k, JSON.stringify(v)]));
  return {
    store,
    get: async (key, type) => {
      const value = store.get(key);
      if (value === undefined) return null;
      return type === "json" ? JSON.parse(value) : value;
    },
    put: async (key, value) => { store.set(key, value); },
  };
}

function makeEnv(kv) {
  return {
    LOKER: kv,
    TELEGRAM_BOT_TOKEN: "t",
    OWNER_CHAT_ID: "100",
    WEBHOOK_SECRET: "hook",
    STATE_SECRET: "state",
  };
}

function telegramRequest(text, { chatId = 100, secret = "hook" } = {}) {
  return new Request("https://w.example/telegram", {
    method: "POST",
    headers: { "X-Telegram-Bot-Api-Secret-Token": secret, "Content-Type": "application/json" },
    body: JSON.stringify({ update_id: 1, message: { chat: { id: chatId }, text } }),
  });
}

function withFakeFetch(fn) {
  const calls = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(url), body: init?.body ? JSON.parse(init.body) : null });
    return new Response(JSON.stringify({ ok: true }), { status: 200 });
  };
  return fn(calls).finally(() => { globalThis.fetch = original; });
}

const CONFIG = { builtin: ["video", "motion"], default_locations: ["Jakarta"] };

test("owner command updates prefs in KV and replies instantly", () => withFakeFetch(async (calls) => {
  const kv = memoryKV({ config: CONFIG });

  const response = await worker.fetch(telegramRequest("/pilih motion"), makeEnv(kv));

  assert.equal(response.status, 200);
  assert.deepEqual(JSON.parse(kv.store.get("prefs")).active, ["motion"]);
  assert.equal(calls.length, 1);
  assert.match(calls[0].url, /sendMessage/);
  assert.equal(calls[0].body.chat_id, "100");
}));

test("rejects webhook calls without the Telegram secret", () => withFakeFetch(async (calls) => {
  const kv = memoryKV({ config: CONFIG });

  const response = await worker.fetch(telegramRequest("/pilih motion", { secret: "x" }), makeEnv(kv));

  assert.equal(response.status, 401);
  assert.equal(kv.store.has("prefs"), false);
  assert.equal(calls.length, 0);
}));

test("ignores messages from other chats", () => withFakeFetch(async (calls) => {
  const kv = memoryKV({ config: CONFIG });

  const response = await worker.fetch(telegramRequest("/pilih motion", { chatId: 999 }), makeEnv(kv));

  assert.equal(response.status, 200);
  assert.equal(kv.store.has("prefs"), false);
  assert.equal(calls.length, 0);
}));

test("state endpoints require the state secret", async () => {
  const kv = memoryKV();
  const response = await worker.fetch(new Request("https://w.example/state"), makeEnv(kv));
  assert.equal(response.status, 401);
});

test("GET /state returns prefs, seen and config", async () => {
  const kv = memoryKV({ config: CONFIG, seen: { "A:1": "x" }, prefs: { active: ["video"], custom: {}, locations: null } });

  const response = await worker.fetch(new Request("https://w.example/state", {
    headers: { Authorization: "Bearer state" },
  }), makeEnv(kv));

  const body = await response.json();
  assert.deepEqual(body.seen, { "A:1": "x" });
  assert.deepEqual(body.prefs.active, ["video"]);
});

test("PUT /state writes seen and config but never prefs", async () => {
  const kv = memoryKV({ prefs: { active: ["video"], custom: {}, locations: null } });

  const response = await worker.fetch(new Request("https://w.example/state", {
    method: "PUT",
    headers: { Authorization: "Bearer state", "Content-Type": "application/json" },
    body: JSON.stringify({ seen: { "A:2": "y" }, config: CONFIG, prefs: { active: [] } }),
  }), makeEnv(kv));

  assert.equal(response.status, 204);
  assert.deepEqual(JSON.parse(kv.store.get("seen")), { "A:2": "y" });
  assert.deepEqual(JSON.parse(kv.store.get("config")), CONFIG);
  assert.deepEqual(JSON.parse(kv.store.get("prefs")).active, ["video"]);
});
