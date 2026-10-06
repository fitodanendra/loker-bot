from typing import Optional


def format_salary_range(start: Optional[int], end: Optional[int]) -> Optional[str]:
    """Format a rupiah range like 'Rp 8.000.000 – 10.000.000'; None when no salary is given."""
    if not start:
        return None
    if not end or end == start:
        return f"Rp {_rupiah(start)}"
    return f"Rp {_rupiah(start)} – {_rupiah(end)}"


def _rupiah(amount: int) -> str:
    return f"{amount:,}".replace(",", ".")
