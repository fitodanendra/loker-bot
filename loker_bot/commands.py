"""Telegram chat commands for choosing which job categories are active."""

HELP = (
    "Perintah yang tersedia:\n"
    "/kategori — lihat kategori aktif\n"
    "/pilih fullstack — HANYA kategori ini (boleh lebih dari satu)\n"
    "/tambah motion — aktifkan kategori\n"
    "/hapus video — matikan kategori\n"
    "/semua — aktifkan semua kategori"
)

Active = frozenset[str]


def handle_command(text: str, categories: tuple[str, ...], active: Active) -> tuple[Active, str]:
    words = text.strip().lower().split()
    if not words or not words[0].startswith("/"):
        return active, HELP
    command = words[0].split("@")[0]
    names = words[1:]

    if command in ("/kategori", "/status", "/start"):
        return active, _status(categories, active)
    if command == "/semua":
        return _changed(frozenset(categories), categories)
    if command in ("/pilih", "/tambah", "/hapus"):
        return _change(command, names, categories, active)
    return active, HELP


def _change(command: str, names: list[str], categories: tuple[str, ...], active: Active):
    if not names:
        return active, f"Tulis nama kategorinya, mis. {command} {categories[0]}\n\n{_status(categories, active)}"
    unknown = [name for name in names if name not in categories]
    if unknown:
        return active, f"Kategori tidak dikenal: {', '.join(unknown)}\n\n{_status(categories, active)}"

    chosen = frozenset(names)
    if command == "/pilih":
        updated = chosen
    elif command == "/tambah":
        updated = active | chosen
    else:
        updated = active - chosen
    if not updated:
        return active, "Minimal satu kategori harus aktif. Pakai /pilih untuk mengganti kategori."
    return _changed(updated, categories)


def _changed(active: Active, categories: tuple[str, ...]):
    return active, "Siap! Mulai pengecekan berikutnya.\n\n" + _status(categories, active)


def _status(categories: tuple[str, ...], active: Active) -> str:
    lines = [f"{'✅' if name in active else '❌'} {name}" for name in categories]
    return "Kategori:\n" + "\n".join(lines) + "\n\n" + HELP
