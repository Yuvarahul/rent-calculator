"""Rent Calculator (CLI)
 
Splits rent, utility bills and shared expenses between flatmates and
prints an itemized amount for each person. Summaries can be exported
to CSV and TXT.
 
Uses only the standard library. The `math` module is used for:
  math.isfinite  - reject inf / nan amounts typed by the user
  math.floor     - convert rupees to whole paise and compute the base share
  math.fmod      - leftover paise after an even split
  math.fsum      - accurate total of all amounts
  math.isclose   - final self-check that the shares add up to the bills
 
Usage: python rent_calculator.py
"""
import csv
import math
from datetime import date, datetime
 
DEFAULT_EXPENSES = ["Electricity", "Water", "Internet"]
 
 
# ---------- money helpers (all amounts are whole paise internally) ----------
 
def to_paise(text: str) -> int:
    """Convert a rupee amount typed by the user to whole paise."""
    value = float(text.replace(",", ""))
    if not math.isfinite(value) or value < 0:
        raise ValueError("Enter a number of 0 or more.")
    return math.floor(value * 100 + 0.5)
 
 
def fmt(paise: int) -> str:
    """Format paise as ₹ with Indian digit grouping, e.g. ₹1,23,456.78."""
    rupees, ps = divmod(paise, 100)
    s = str(rupees)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups + [tail])
    return f"₹{s}.{ps:02d}"
 
 
def split_amount(total: int, count: int, offset: int = 0) -> list:
    """Split `total` paise among `count` people so the shares add up exactly.
 
    Leftover paise are handed out one each, starting from a different
    person for each call (controlled by `offset`) so nobody is always
    the one who pays the extra paisa.
    """
    base = math.floor(total / count)
    extra = int(math.fmod(total, count))
    shares = [base + (1 if (i - offset) % count < extra else 0)
              for i in range(count)]
    assert sum(shares) == total
    return shares
 
 
# ---------- input helpers ----------
 
def ask_amount(prompt: str, allow_blank: bool = False) -> int:
    while True:
        text = input(prompt).strip()
        if text == "" and allow_blank:
            return 0
        try:
            return to_paise(text)
        except ValueError:
            print("  Invalid amount. Enter a number of 0 or more, for example 12500 or 849.50.")
 
 
def ask_yes_no(prompt: str) -> bool:
    return input(prompt).strip().lower() in ("y", "yes")
 
 
def ask_month() -> str:
    while True:
        text = input("Month (YYYY-MM, Enter for this month): ").strip()
        if not text:
            return date.today().strftime("%Y-%m")
        try:
            datetime.strptime(text, "%Y-%m")
            return text
        except ValueError:
            print("  Use the format YYYY-MM, for example 2026-11.")
 
 
def ask_members() -> list:
    while True:
        text = input("How many flatmates? ").strip()
        if text.isdigit() and int(text) >= 1:
            count = int(text)
            break
        print("  Enter a whole number of 1 or more.")
    names = []
    for i in range(count):
        name = input(f"  Name of flatmate {i + 1}: ").strip()
        names.append(name or f"Flatmate {i + 1}")
    return names
 
 
def ask_sharers(expense: str, names: list) -> list:
    """Return the indices of the people who share this expense."""
    while True:
        text = input(f"  Who shares {expense}? Numbers like 1,3 (Enter for everyone): ").strip()
        if not text:
            return list(range(len(names)))
        try:
            picks = sorted({int(p) for p in text.replace(" ", "").split(",")})
        except ValueError:
            print("  Use numbers separated by commas, for example 1,3.")
            continue
        if picks and all(1 <= p <= len(names) for p in picks):
            return [p - 1 for p in picks]
        print(f"  Choose numbers between 1 and {len(names)}.")
 
 
# ---------- calculation ----------
 
def calculate(names, rent_mode, rent_input, expenses):
    """Return per-person line items and totals.
 
    rent_input: total rent in paise (equal mode) or a list of rents (custom mode)
    expenses:   list of (label, amount_paise, [member indices])
    """
    n = len(names)
    lines = [[] for _ in range(n)]
 
    rent_shares = split_amount(rent_input, n) if rent_mode == "equal" else rent_input
    for i in range(n):
        lines[i].append(("Rent", rent_shares[i]))
 
    for idx, (label, amount, who) in enumerate(expenses):
        shares = split_amount(amount, len(who), idx)
        by_person = dict(zip(who, shares))
        for i in range(n):
            lines[i].append((label, by_person.get(i, 0)))
 
    totals = [sum(a for _, a in person) for person in lines]
 
    # Self-check: the shares must add up to what was entered
    expected = sum(rent_shares) + sum(a for _, a, _ in expenses)
    assert sum(totals) == expected
    assert math.isclose(math.fsum(totals) / 100, expected / 100, abs_tol=1e-9)
    return lines, totals
 
 
# ---------- output ----------
 
def print_summary(month, names, lines, totals):
    print(f"\n=== Rent summary: {month} ===")
    for name, person, total in zip(names, lines, totals):
        print(f"\n{name}: {fmt(total)}")
        for label, amount in person:
            print(f"  {label:<20}{fmt(amount):>16}")
    print(f"\nTotal for the house: {fmt(sum(totals))}")
 
 
def export_csv(path, names, lines, totals):
    labels = [label for label, _ in lines[0]]
    col_totals = [sum(person[j][1] for person in lines) for j in range(len(labels))]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Member"] + labels + ["Total"])
        for name, person, total in zip(names, lines, totals):
            w.writerow([name] + [f"{a / 100:.2f}" for _, a in person] + [f"{total / 100:.2f}"])
        w.writerow(["Total"] + [f"{c / 100:.2f}" for c in col_totals] + [f"{sum(totals) / 100:.2f}"])
 
 
def export_txt(path, month, names, lines, totals):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Rent summary: {month}\n{'=' * 32}\n\n")
        for name, person, total in zip(names, lines, totals):
            f.write(f"{name}: {fmt(total)}\n")
            for label, amount in person:
                f.write(f"  {label}: {fmt(amount)}\n")
            f.write("\n")
        f.write(f"Total for the house: {fmt(sum(totals))}\n")
 
 
# ---------- main ----------
 
def main():
    print("=== Rent Calculator ===")
    month = ask_month()
    names = ask_members()
 
    print("\nRent split: 1) equally   2) set each person's rent")
    while True:
        choice = input("Choose 1 or 2: ").strip()
        if choice in ("1", "2"):
            break
        print("  Enter 1 or 2.")
    if choice == "1":
        rent_mode = "equal"
        rent_input = ask_amount("Total monthly rent (₹): ")
    else:
        rent_mode = "custom"
        rent_input = [ask_amount(f"  Rent for {name} (₹): ") for name in names]
 
    print("\nUtilities and shared expenses (press Enter to skip one)")
    for i, name in enumerate(names, 1):
        print(f"  {i}. {name}")
    expenses = []
    for label in DEFAULT_EXPENSES:
        amount = ask_amount(f"{label} bill (₹): ", allow_blank=True)
        if amount:
            expenses.append((label, amount, ask_sharers(label, names)))
    while ask_yes_no("\nAdd another shared expense? (y/N): "):
        label = input("  Expense name: ").strip() or "Other"
        amount = ask_amount(f"  {label} amount (₹): ")
        if amount:
            expenses.append((label, amount, ask_sharers(label, names)))
 
    lines, totals = calculate(names, rent_mode, rent_input, expenses)
    print_summary(month, names, lines, totals)
 
    if ask_yes_no("\nExport the summary to CSV and TXT? (y/N): "):
        base = f"rent-summary-{month}"
        export_csv(f"{base}.csv", names, lines, totals)
        export_txt(f"{base}.txt", month, names, lines, totals)
        print(f"Saved {base}.csv and {base}.txt in the current folder.")
 
 
if __name__ == "__main__":
    main()
 
