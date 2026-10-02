// Telegram chat commands: categories (/pilih, /tambah, /hapus, /semua, /kategori),
// custom categories (/baru, /buang) and locations (/lokasi, /tambahlokasi, ...).
// Pure functions: they take the current prefs and return new prefs plus a reply.

export const MAX_CUSTOM = 10;
const MAX_KEYWORD_LENGTH = 60;
const MAX_LOCATION_LENGTH = 40;

export const HELP = [
  "Perintah yang tersedia:",
  "/kategori — lihat kategori aktif",
  "/pilih fullstack — HANYA kategori ini (boleh lebih dari satu)",
  "/tambah motion — aktifkan kategori",
  "/hapus video — matikan kategori",
  "/semua — aktifkan semua kategori",
  "/baru graphic designer — buat kategori baru",
  "/buang graphicdesigner — hapus kategori buatan sendiri",
  "/lokasi — atur lokasi lowongan",
].join("\n");

const LOCATION_HELP = [
  "/lokasi — lihat lokasi aktif",
  "/tambahlokasi bandung — tambah lokasi",
  "/hapuslokasi bogor — hapus lokasi",
  "/semualokasi — seluruh Indonesia",
].join("\n");

export const BOT_COMMANDS = [
  ["kategori", "Lihat kategori aktif"],
  ["pilih", "Hanya kategori ini, mis. /pilih fullstack"],
  ["tambah", "Aktifkan kategori, mis. /tambah motion"],
  ["hapus", "Matikan kategori, mis. /hapus video"],
  ["semua", "Aktifkan semua kategori"],
  ["baru", "Buat kategori baru, mis. /baru graphic designer"],
  ["buang", "Hapus kategori buatan sendiri"],
  ["lokasi", "Lihat lokasi aktif"],
  ["tambahlokasi", "Tambah lokasi, mis. /tambahlokasi bandung"],
  ["hapuslokasi", "Hapus lokasi, mis. /hapuslokasi bogor"],
  ["semualokasi", "Cari di seluruh Indonesia"],
];

export function defaultPrefs(builtin) {
  return { active: [...builtin], custom: {}, locations: null };
}

/**
 * @param {string} text  message text from Telegram
 * @param {{builtin: string[], defaultLocations: string[], prefs: object}} ctx
 * @returns {{prefs: object, reply: string, changed: boolean}}
 */
export function handleText(text, { builtin, defaultLocations, prefs }) {
  const words = text.trim().split(/\s+/).filter(Boolean);
  const command = (words[0] || "").toLowerCase().split("@")[0];
  const argument = words.slice(1).join(" ");
  const state = { builtin, defaultLocations, prefs };

  const handler = HANDLERS[command];
  if (!handler) return unchanged(prefs, HELP);
  return handler(argument, state);
}

const HANDLERS = {
  "/start": (_, s) => unchanged(s.prefs, status(s)),
  "/kategori": (_, s) => unchanged(s.prefs, status(s)),
  "/status": (_, s) => unchanged(s.prefs, status(s)),
  "/semua": (_, s) => changedActive(s, allCategories(s)),
  "/pilih": (arg, s) => changeActive("/pilih", arg, s),
  "/tambah": (arg, s) => changeActive("/tambah", arg, s),
  "/hapus": (arg, s) => changeActive("/hapus", arg, s),
  "/baru": (arg, s) => createCustom(arg.toLowerCase(), s),
  "/buang": (arg, s) => removeCustom(arg.toLowerCase(), s),
  "/lokasi": (_, s) => unchanged(s.prefs, describeLocations(currentLocations(s)) + "\n\n" + LOCATION_HELP),
  "/semualokasi": (_, s) => changedLocations(s, [], "✅ Lokasi diubah."),
  "/tambahlokasi": (arg, s) => addLocation(titleCase(arg).slice(0, MAX_LOCATION_LENGTH), s),
  "/hapuslokasi": (arg, s) => removeLocation(titleCase(arg), s),
};

// --- helpers ---------------------------------------------------------------

export function categoryName(text) {
  return text.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");
}

function unchanged(prefs, reply) {
  return { prefs, reply, changed: false };
}

function withPrefs(state, patch, reply) {
  return { prefs: { ...state.prefs, ...patch }, reply, changed: true };
}

function allCategories(state) {
  return [...state.builtin, ...Object.keys(state.prefs.custom)];
}

function categoryList(categories, active) {
  const activeSet = new Set(active);
  const lines = categories.map((name) => `${activeSet.has(name) ? "✅" : "❌"} ${name}`);
  return "Kategori:\n" + lines.join("\n");
}

function status(state) {
  return categoryList(allCategories(state), state.prefs.active) + "\n\n" + HELP;
}

// --- categories ------------------------------------------------------------

function changedActive(state, active) {
  const next = { ...state, prefs: { ...state.prefs, active } };
  return withPrefs(state, { active }, "Siap! Mulai pengecekan berikutnya.\n\n" + status(next));
}

function changeActive(command, argument, state) {
  const categories = allCategories(state);
  const names = argument.split(/\s+/).map(categoryName).filter(Boolean);
  if (names.length === 0) {
    return unchanged(state.prefs, `Tulis nama kategorinya, mis. ${command} ${categories[0]}\n\n${status(state)}`);
  }
  const unknown = names.filter((name) => !categories.includes(name));
  if (unknown.length > 0) {
    return unchanged(state.prefs, `Kategori tidak dikenal: ${unknown.join(", ")}\n\n${status(state)}`);
  }

  const current = new Set(state.prefs.active);
  let updated;
  if (command === "/pilih") updated = new Set(names);
  else if (command === "/tambah") updated = new Set([...current, ...names]);
  else updated = new Set([...current].filter((name) => !names.includes(name)));

  if (updated.size === 0) {
    return unchanged(state.prefs, "Minimal satu kategori harus aktif. Pakai /pilih untuk mengganti kategori.");
  }
  return changedActive(state, categories.filter((name) => updated.has(name)));
}

// --- custom categories -----------------------------------------------------

function createCustom(keyword, state) {
  const name = categoryName(keyword);
  const { custom } = state.prefs;
  if (!name) return unchanged(state.prefs, "Tulis kata kuncinya, mis. /baru graphic designer");
  if (keyword.length > MAX_KEYWORD_LENGTH) {
    return unchanged(state.prefs, `Kata kunci terlalu panjang (maks. ${MAX_KEYWORD_LENGTH} huruf).`);
  }
  if (state.builtin.includes(name) || name in custom) {
    return unchanged(state.prefs, `Kategori “${name}” sudah ada. Pakai /tambah ${name} untuk menyalakannya.`);
  }
  if (Object.keys(custom).length >= MAX_CUSTOM) {
    return unchanged(state.prefs, `Maksimal ${MAX_CUSTOM} kategori buatan sendiri. /buang salah satu dulu.`);
  }

  const newCustom = { ...custom, [name]: keyword };
  const newActive = [...new Set([...state.prefs.active, name])];
  const reply = [
    `✅ Kategori baru “${name}” dibuat dan dinyalakan.`,
    `Bot akan mencari “${keyword}” dan hanya mengirim lowongan yang judulnya mengandung semua kata: ${keyword.split(/\s+/).join(", ")}.`,
    "Kategori lain tidak berubah. Hasilnya muncul di pengecekan berikutnya.",
    "",
    categoryList([...state.builtin, ...Object.keys(newCustom)], newActive),
  ].join("\n");
  return withPrefs(state, { custom: newCustom, active: newActive }, reply);
}

function removeCustom(keyword, state) {
  const name = categoryName(keyword);
  const { custom } = state.prefs;
  if (state.builtin.includes(name)) {
    return unchanged(state.prefs, `“${name}” kategori bawaan, tidak bisa dibuang. Pakai /hapus ${name} untuk mematikannya.`);
  }
  if (!(name in custom)) {
    const names = Object.keys(custom).join(", ") || "(belum ada)";
    return unchanged(state.prefs, `Kategori buatan “${name || "-"}” tidak ditemukan. Kategori buatan Anda: ${names}`);
  }

  const remaining = Object.fromEntries(Object.entries(custom).filter(([key]) => key !== name));
  const categories = [...state.builtin, ...Object.keys(remaining)];
  let newActive = state.prefs.active.filter((active) => active !== name);
  if (newActive.length === 0) newActive = categories;
  const reply = `🗑 Kategori “${name}” dibuang.\n\n${categoryList(categories, newActive)}`;
  return withPrefs(state, { custom: remaining, active: newActive }, reply);
}

// --- locations -------------------------------------------------------------

function currentLocations(state) {
  return state.prefs.locations ?? state.defaultLocations;
}

export function describeLocations(locations) {
  if (locations.length === 0) return "📍 Lokasi: Seluruh Indonesia (+ remote)";
  return "📍 Lokasi: " + locations.join(", ") + " (+ remote)";
}

function changedLocations(state, locations, headline) {
  return withPrefs(state, { locations }, `${headline}\n\n${describeLocations(locations)}`);
}

function locationIndex(place, locations) {
  return locations.findIndex((existing) => existing.toLowerCase() === place.toLowerCase());
}

function addLocation(place, state) {
  const current = currentLocations(state);
  if (!place) return unchanged(state.prefs, "Tulis nama lokasinya, mis. /tambahlokasi bandung");
  if (locationIndex(place, current) >= 0) {
    return unchanged(state.prefs, `${place} sudah ada.\n\n${describeLocations(current)}`);
  }
  return changedLocations(state, [...current, place], `✅ ${place} ditambahkan.`);
}

function removeLocation(place, state) {
  const current = currentLocations(state);
  const index = locationIndex(place, current);
  if (!place || index < 0) {
    return unchanged(state.prefs, `Lokasi “${place || "-"}” tidak ada di daftar.\n\n${describeLocations(current)}`);
  }
  if (current.length === 1) {
    return unchanged(state.prefs, "Minimal satu lokasi. Pakai /semualokasi untuk seluruh Indonesia.");
  }
  const updated = current.filter((_, i) => i !== index);
  return changedLocations(state, updated, `🗑 ${current[index]} dihapus.`);
}

function titleCase(text) {
  return text.trim().toLowerCase().replace(/(^|\s)\p{L}/gu, (match) => match.toUpperCase());
}
