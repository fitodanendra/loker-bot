// Cloudflare Worker for loker-bot.
//   POST /telegram  Telegram webhook: answers chat commands instantly, stores prefs in KV.
//   GET  /state     (bot only) prefs + seen jobs + config for the GitHub Actions job.
//   PUT  /state     (bot only) saves seen jobs and config. Never touches prefs.
//   POST /setup     (bot only) registers the webhook and the command menu with Telegram.

import { BOT_COMMANDS, defaultPrefs, handleText } from "./commands.js";

const TELEGRAM_API = "https://api.telegram.org/bot";
const EMPTY_CONFIG = { builtin: [], default_locations: [] };

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    try {
      if (pathname === "/telegram" && request.method === "POST") return await onTelegram(request, env);
      if (pathname === "/state" && request.method === "GET") return await guarded(request, env, getState);
      if (pathname === "/state" && request.method === "PUT") return await guarded(request, env, putState);
      if (pathname === "/setup" && request.method === "POST") return await guarded(request, env, setup);
      return new Response("Not found", { status: 404 });
    } catch (error) {
      console.error(`${request.method} ${pathname} failed:`, error);
      return new Response("Internal error", { status: 500 });
    }
  },
};

// --- Telegram webhook --------------------------------------------------------

async function onTelegram(request, env) {
  const secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token") || "";
  if (!safeEqual(secret, env.WEBHOOK_SECRET)) return new Response("Unauthorized", { status: 401 });

  const update = await request.json().catch(() => null);
  const message = update?.message;
  const isOwner = String(message?.chat?.id) === String(env.OWNER_CHAT_ID);
  if (!isOwner || typeof message?.text !== "string") return new Response("ok");

  const config = (await env.LOKER.get("config", "json")) || EMPTY_CONFIG;
  const prefs = (await env.LOKER.get("prefs", "json")) || defaultPrefs(config.builtin);
  const result = handleText(message.text, {
    builtin: config.builtin,
    defaultLocations: config.default_locations,
    prefs,
  });

  if (result.changed) await env.LOKER.put("prefs", JSON.stringify(result.prefs));
  await telegram(env, "sendMessage", { chat_id: String(env.OWNER_CHAT_ID), text: result.reply });
  // Always 200 so Telegram does not retry the same update.
  return new Response("ok");
}

// --- endpoints for the GitHub Actions job ----------------------------------

async function guarded(request, env, handler) {
  const auth = request.headers.get("Authorization") || "";
  if (!safeEqual(auth, `Bearer ${env.STATE_SECRET}`)) return new Response("Unauthorized", { status: 401 });
  return handler(request, env);
}

async function getState(_request, env) {
  const [prefs, seen, config] = await Promise.all([
    env.LOKER.get("prefs", "json"),
    env.LOKER.get("seen", "json"),
    env.LOKER.get("config", "json"),
  ]);
  return Response.json({ prefs, seen: seen || {}, config });
}

async function putState(request, env) {
  const body = await request.json().catch(() => null);
  if (!body || typeof body !== "object") return new Response("Bad request", { status: 400 });

  const writes = [];
  if (isPlainObject(body.seen)) writes.push(env.LOKER.put("seen", JSON.stringify(body.seen)));
  if (isPlainObject(body.config)) writes.push(env.LOKER.put("config", JSON.stringify(body.config)));
  await Promise.all(writes);
  return new Response(null, { status: 204 });
}

async function setup(request, env) {
  const origin = new URL(request.url).origin;
  const webhook = await telegram(env, "setWebhook", {
    url: `${origin}/telegram`,
    secret_token: env.WEBHOOK_SECRET,
    allowed_updates: ["message"],
    drop_pending_updates: false,
  });
  const commands = await telegram(env, "setMyCommands", {
    commands: BOT_COMMANDS.map(([command, description]) => ({ command, description })),
  });
  return Response.json({ webhook: webhook.ok, commands: commands.ok });
}

// --- utilities ---------------------------------------------------------------

async function telegram(env, method, payload) {
  const response = await fetch(`${TELEGRAM_API}${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => ({ ok: false }));
  if (!body.ok) console.error(`Telegram ${method} failed with HTTP ${response.status}`);
  return body;
}

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function safeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || !b) return false;
  const left = new TextEncoder().encode(a);
  const right = new TextEncoder().encode(b);
  let diff = left.length ^ right.length;
  for (let i = 0; i < Math.max(left.length, right.length); i++) {
    diff |= (left[i] ?? 0) ^ (right[i] ?? 0);
  }
  return diff === 0;
}
