from typing import Optional


def format_salary_range(
    start: Optional[float], end: Optional[float],
    currency: str = "Rp", period: Optional[str] = None,
) -> Optional[str]:
    """Format a range like 'Rp 8.000.000 – 10.000.000' or 'USD 50 – 150 / jam'.

    Returns None when no salary is given.
    """
    if not start:
        return None
    amount = _number(start) if not end or end == start else f"{_number(start)} – {_number(end)}"
    suffix = f" / {period}" if period else ""
    return f"{currency} {amount}{suffix}"


def _number(amount: float) -> str:
    return f"{round(amount):,}".replace(",", ".")
