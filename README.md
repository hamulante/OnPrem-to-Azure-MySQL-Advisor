# OnPrem-to-Azure-MySQL-Advisor

A **pre-decision sizing & risk advisor** for migrating self-managed / on-prem MySQL to
**Azure Database for MySQL Flexible Server**.

You feed it your current server's specs and workload profile. It returns a recommended
SKU tier, IOPS/storage sizing, a parameter-compatibility report, and a list of hard
blockers — **before** you commit to the migration.

> Scope boundary: this advises **whether and how to size** the move. It does **not**
> move data. Execution is already well served by [Azure DMS](https://learn.microsoft.com/azure/dms/)
> and [MySQL Import](https://learn.microsoft.com/azure/mysql/migrate/).

---

## "There are already migration docs. Why do I need this?"

Microsoft's docs are excellent at telling you **how to move the bytes**. They do not tell
you, for *your specific server*, the three questions that actually decide success:

| Question you actually have | What the docs give you | What this advisor gives you |
|---|---|---|
| **Which SKU do I pick?** | A feature/limit matrix for all tiers | A concrete recommendation for *your* vCore / memory / IOPS / storage, derived from your workload |
| **What will break after I move?** | A scattered list of "unsupported" notes across many pages | One consolidated compatibility report against *your* current config |
| **What will hard-fail the migration?** | Generic prerequisites | The specific blockers that apply to *you*, surfaced up front |

The docs are a **generic how-to**. This is a **personalized what-for-you + what-could-go-wrong**.

A migration guide is a map of the road. This is the part that says *"with your load, take a
D-series with provisioned IOPS, and by the way these 3 settings of yours won't survive the trip."*

---

## The three things it checks for you

1. **Sizing** — maps your CPU / memory / disk / IOPS / connection usage onto a recommended
   Flexible Server tier (Burstable / General Purpose / Business Critical) with justified
   IOPS and storage estimates. IOPS on Flexible Server is tied to storage size / provisioned
   IOPS, *not* to vCore — a classic mistake this is built to catch.

2. **Parameter & feature compatibility** — diffs your current MySQL settings against what
   Flexible Server actually allows. Flags the well-known traps, e.g.:
   - no `SUPER` privilege / no `root`
   - `lower_case_table_names` is fixed at creation time and cannot be changed later
   - parameters that are not-exposed, read-only, or require a restart
   - `innodb_buffer_pool_size` being derived from the chosen memory tier

3. **Blockers** — things that will stop a migration before it starts, so you find them on
   day zero instead of mid-cutover.

Output: a structured report (machine-readable + human summary).

---

## Why a deterministic core, not "just ask an LLM"

Sizing numbers and platform limits must be **reproducible and sourced** — a tool that
hallucinates an IOPS ceiling is worse than no tool.

- The decision logic (SKU selection, IOPS/storage math, parameter diff) lives in a
  **deterministic, unit-tested core**. Same input → same recommendation, every time.
- An LLM is used only at the edges: parsing free-form input and explaining the result in
  plain language. It never invents a spec number.
- Every Azure limit or default cited by the tool is **traceable to an official source**.
  Anything unverified is marked as a placeholder, not shipped as fact.

---

## Status

Early. Decision rules grow one real migration pitfall at a time, each backed by a test.
This is intentionally **not** a generic framework built up front.

## Project layout

```
advisor/
  core.py        # decision engine (the single source of rules)
  models.py      # dataclass inputs / outputs
  specs/         # Azure SKU / parameter spec data (each value source-tagged)
cli.py           # command-line front end
tests/           # pytest — one case per rule
```
