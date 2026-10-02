"""/lokasi commands: choose which cities jobs must be in. An empty list means all of Indonesia."""

from typing import Optional

Locations = tuple[str, ...]

HELP = (
    "/lokasi — lihat lokasi aktif\n"
    "/tambahlokasi bandung — tambah lokasi\n"
    "/hapuslokasi bogor — hapus lokasi\n"
    "/semualokasi — seluruh Indonesia"
)
MAX_NAME_LENGTH = 40


def handle_location_command(text: str, current: Locations) -> Optional[tuple[Locations, str]]:
    words = text.strip().split()
    if not words:
        return None
    command = words[0].lower().split("@")[0]
    place = " ".join(words[1:]).strip().title()[:MAX_NAME_LENGTH]

    if command == "/lokasi":
        return current, describe(current) + "\n\n" + HELP
    if command == "/semualokasi":
        return (), "✅ Lokasi diubah.\n\n" + describe(())
    if command == "/tambahlokasi":
        return _add(place, current)
    if command == "/hapuslokasi":
        return _remove(place, current)
    return None


def describe(locations: Locations) -> str:
    if not locations:
        return "📍 Lokasi: Seluruh Indonesia (+ remote)"
    return "📍 Lokasi: " + ", ".join(locations) + " (+ remote)"


def _add(place: str, current: Locations):
    if not place:
        return current, "Tulis nama lokasinya, mis. /tambahlokasi bandung"
    if _index(place, current) is not None:
        return current, f"{place} sudah ada.\n\n" + describe(current)
    updated = current + (place,)
    return updated, f"✅ {place} ditambahkan.\n\n" + describe(updated)


def _remove(place: str, current: Locations):
    index = _index(place, current)
    if not place or index is None:
        return current, f"Lokasi “{place or '-'}” tidak ada di daftar.\n\n" + describe(current)
    if len(current) == 1:
        return current, "Minimal satu lokasi. Pakai /semualokasi untuk seluruh Indonesia."
    updated = current[:index] + current[index + 1:]
    return updated, f"🗑 {current[index]} dihapus.\n\n" + describe(updated)


def _index(place: str, current: Locations) -> Optional[int]:
    lowered = [existing.lower() for existing in current]
    return lowered.index(place.lower()) if place.lower() in lowered else None
