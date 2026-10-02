"""/baru and /buang: categories the user creates from Telegram (stored in prefs.json)."""

from typing import Optional

from loker_bot.models import Search

MAX_CUSTOM = 10
MAX_KEYWORD_LENGTH = 60

Custom = dict[str, str]  # category name -> search keyword
Result = tuple[Custom, frozenset[str], str]


def category_name(keyword: str) -> str:
    return "".join(char for char in keyword.lower() if char.isalnum())


def handle_custom_command(
    text: str, builtin: tuple[str, ...], custom: Custom, active: frozenset[str],
) -> Optional[Result]:
    words = text.strip().split()
    if not words:
        return None
    command = words[0].lower().split("@")[0]
    keyword = " ".join(words[1:]).lower()
    if command == "/baru":
        return _create(keyword, builtin, custom, active)
    if command == "/buang":
        return _remove(keyword, builtin, custom, active)
    return None


def _create(keyword: str, builtin, custom: Custom, active) -> Result:
    name = category_name(keyword)
    if not name:
        return custom, active, "Tulis kata kuncinya, mis. /baru graphic designer"
    if len(keyword) > MAX_KEYWORD_LENGTH:
        return custom, active, f"Kata kunci terlalu panjang (maks. {MAX_KEYWORD_LENGTH} huruf)."
    if name in builtin or name in custom:
        return custom, active, f"Kategori “{name}” sudah ada. Pakai /tambah {name} untuk menyalakannya."
    if len(custom) >= MAX_CUSTOM:
        return custom, active, f"Maksimal {MAX_CUSTOM} kategori buatan sendiri. /buang salah satu dulu."
    reply = (
        f"✅ Kategori baru “{name}” dibuat dan dinyalakan.\n"
        f"Bot akan mencari “{keyword}” dan hanya mengirim lowongan yang judulnya "
        f"mengandung semua kata: {', '.join(keyword.split())}.\n"
        "Hasilnya muncul di pengecekan berikutnya."
    )
    return {**custom, name: keyword}, active | {name}, reply


def _remove(keyword: str, builtin, custom: Custom, active) -> Result:
    name = category_name(keyword)
    if name in builtin:
        return custom, active, f"“{name}” kategori bawaan, tidak bisa dibuang. Pakai /hapus {name} untuk mematikannya."
    if name not in custom:
        names = ", ".join(custom) or "(belum ada)"
        return custom, active, f"Kategori buatan “{name or '-'}” tidak ditemukan. Kategori buatan Anda: {names}"
    remaining = {key: value for key, value in custom.items() if key != name}
    new_active = active - {name}
    if not new_active:
        new_active = frozenset(builtin) | frozenset(remaining)
    return remaining, new_active, f"🗑 Kategori “{name}” dibuang."


def custom_searches(custom: Custom) -> list[Search]:
    return [
        Search(query=keyword, name=name, title_must_include_all=tuple(keyword.split()))
        for name, keyword in custom.items()
    ]
