"""Checks of the whole-night model in scripts/reference/nights.py (the Family
class) against the data files and the rules in docs/night.md.

Usage: python -I night_check.py <reference dir> <data dir>
"""
import os
import re
import sys

sys.path.insert(0, sys.argv[1])
import nights as N
import travspec as T

data = sys.argv[2]
read = lambda name: open(os.path.join(data, name), encoding="utf-8", newline="").read()
texts = {m.group(1): m.group(2) for m in re.finditer(r'<item id="([^"]+)">\s*<t>(.*?)</t>', read("Text.xml"), re.S)}
lib = N.NightLib(read("Nights.txt"))
table, _, _ = T.load(data)
problems = []

needed = ["budget_savings", "budget_salary", "budget_penalties", "budget_bribes", "budget_rent", "budget_food",
          "budget_heat", "budget_medicine", "family_verysick_1", "family_verysick_many", "family_sick_1",
          "family_sick_many"] + ["family_%s_%s" % (m, k) for m in ("wife", "son", "mil", "uncle", "niece")
                                 for k in ("status", "message", "budget")] + \
         ["family_died_%d" % n for n in range(1, 6)]
missing = [k for k in needed if k not in texts]
print("-- text entries the night code asks for: %d, missing: %s" % (len(needed), missing or "none"))
problems += ["text entry missing: " + k for k in missing]


def show(family, title):
    print("  " + title)
    for line in family.budget.lines:
        print("      [%s] %-18s %+4d  %s" % ("x" if line.enabled else " ", line.name, line.cost, line.must_pay))
    print("      total %d, profit %s, messages: %s" % (family.budget.total, family.facts.get("Night/Profit"),
                                                      family.messages))


print("\n-- night 1: eight travelers paid, nothing else --")
facts = {}
family = N.Family(lib, facts, N.Summary(1, paid=8, night_event_ids=["MANAGE_EXPENSES"]), texts)
show(family, "budget as first shown")
expect = [("SALARY (8)", 40), ("SAVINGS", 30), ("RENT", -20)]
if sorted((l.name, l.cost) for l in family.budget.lines[:3]) != sorted(expect):
    problems.append("night 1: the first three lines are not savings, salary and rent")
if family.budget.total != 30 + 40 - 20 - 20 - 10:
    problems.append("night 1 total")
family.balance = family.budget.balance()
family.apply_budget()
print("      after sleeping: savings %s, alive %s, wife: %s, ending: %s" % (
    facts["Night/Savings"], facts["Night/FamilyAlive"], facts["Night/wife"], family.want_end_id))
if facts["Night/Savings"] != "20" or family.want_end_id is not None:
    problems.append("night 1 result")

print("\n-- a poor night: two travelers paid, savings 5, rent raised --")
facts = {"Night/Savings": "5"}
family = N.Family(lib, facts, N.Summary(4, paid=2, night_event_ids=["APARTMENT_RENT"]), texts)
show(family, "before balancing (rent already 25: the rent line is set early)")
if not any(l.name == "RENT" and l.cost == -25 for l in family.budget.lines):
    problems.append("the raised rent is not in the budget of the same night")
rejected = family.budget.balance()
show(family, "after balancing (last line unticked: index %s)" % rejected)
if family.budget.total < 0 and any(l.enabled and l.must_pay != N.MUST_PAY for l in family.budget.lines):
    problems.append("balance left an optional line ticked while in debt")
family.apply_budget()
print("      after sleeping: savings %s, members: %s, ending: %s" % (
    facts["Night/Savings"], {m.id: (m.value, m.emotions()) for m in family.members}, family.want_end_id))

print("\n-- starving the family: never paying for food or heat --")
facts = {}
day = 1
deaths = {}
while day <= 12:
    family = N.Family(lib, facts, N.Summary(day, paid=10), texts)
    for line in family.budget.lines:
        if line.name in ("FOOD", "HEAT") or line.name.startswith("MEDICINE"):
            line.enabled = False
    family.apply_budget()
    for m in family.members:
        if m.just_died:
            deaths[m.id] = day
    if family.want_end_id:
        break
    day += 1
print("  night each member dies:", deaths, "| ending %r on night %d" % (family.want_end_id, day))
if family.want_end_id != "family-dead" or len(deaths) != 4:
    problems.append("starving did not end with the family dead")
family = N.Family(lib, dict(facts), N.Summary(day + 1, paid=0), texts)
print("  the following night's messages would be:", family.messages)

print("\n-- sickness and medicine --")
facts = {"Night/son": "sick=3 hungry=0 cold=0", "Night/wife": "sick=1 hungry=0 cold=0"}
family = N.Family(lib, facts, N.Summary(6, paid=10), texts)
show(family, "son very sick, wife sick")
if "Your son will die without medicine." not in family.messages:
    problems.append("the very-sick message is missing")
if not {"MEDICINE (SON)", "MEDICINE (WIFE)"} <= {l.name for l in family.budget.lines}:
    problems.append("medicine lines missing")
family.apply_budget()
print("      after paying for both:", facts["Night/son"], "|", facts["Night/wife"])

print("\n-- debt --")
facts = {"Night/Savings": "0"}
family = N.Family(lib, facts, N.Summary(9, paid=1, penalties=3, penalty_cost=15), texts)
family.budget.balance()
show(family, "one traveler, three penalties")
family.apply_budget()
print("      ending:", family.want_end_id, "| savings", facts["Night/Savings"])
if family.want_end_id != "in-debt":
    problems.append("debt did not give the in-debt ending")

print("\n-- attack and unpaid travelers --")
family = N.Family(lib, {}, N.Summary(3, paid=4, unpaid=2, attack_result="SOLVED"), texts)
show(family, "attack stopped, two travelers after 6PM")
if not any(l.name == "SHARPSHOOTER BONUS" for l in family.budget.lines) or \
        "Applicants entering after 6PM are unpaid." not in family.messages:
    problems.append("attack bonus or the 6PM message is missing")
family.apply_budget()
again = N.Family(lib, family.facts, N.Summary(4, paid=4, unpaid=1), texts)
print("      the 6PM message is shown again the next time:", "Applicants entering after 6PM are unpaid." in again.messages)

print("\n-- every story day's own night events run without error --")
facts = {"Game/Device": "desktop"}
for col in table.col_ids[1:]:
    if not col.isdigit() or int(col) > 31:
        continue
    day = int(col)
    facts["Game/Day"] = str(day)
    ids = T.split_and_trim(table.cell(day, "NIGHTEVENTS"), "\n")
    try:
        family = N.Family(lib, facts, N.Summary(day, paid=9, night_event_ids=ids, escape_passports=1 if day > 28 else 0), texts)
        family.budget.balance()
        family.apply_budget()
    except Exception as e:                                   # noqa: BLE001
        problems.append("day %d: %r" % (day, e))
        break
    extra = [l.name for l in family.budget.lines if l.yes_no_op is not None or
             l.name not in ("SAVINGS", "RENT", "FOOD", "HEAT") and not l.name.startswith(("SALARY", "MEDICINE"))]
    if ids or extra or family.calendar.get_events(day):
        print("  night %2d: events %s + scheduled %s -> extra lines %s, savings %s%s" % (
            day, ids, family.calendar.get_events(day), extra, facts["Night/Savings"],
            ", ending " + family.want_end_id if family.want_end_id else ""))
print("  calendar left at the end:", facts.get("Night/Calendar"))

print("\nproblems:", sorted(set(problems)) or "none")
