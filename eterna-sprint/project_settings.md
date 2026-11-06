The settings of the Eterna Sprint GitHub Project are not under source control,
so are recorded here in case they get corrupted/lost.

📅 Last updated: _not yet created - fill in once Phase 0 (manual project
creation) is complete._

# Short description

TODO: fill in once the project exists.

# README

TODO: fill in once the project exists.

# Views

## 1️⃣ Sprint board (List, sliced by Repository)

- Filter: none (all tracked Issues/PRs across repos)
- Sliced by: `Repository`
- NOT Kanban - this is the working list, grouped per-repo via slicing.
- RISK (unverified): assumes GitHub Projects v2 auto-populates a sliceable
  `Repository` meta-field for multi-repo projects. Confirm once the project
  is created; if this field isn't sliceable, a custom field + partial
  Peloton-style sync would need to be reintroduced.

## 2️⃣ Active (Kanban, cross-repo)

- Filter: `Status` = whichever value(s) the team agrees represents "active"
  work (e.g. "In Progress"/"In Review").
- Grouped by: `Status`
- The ONLY view grouped/displayed as a Kanban board.
- `Status` is set manually by the team - `update_project.py` never writes it.

## 3️⃣ Assigned or review requested (List, cross-repo)

- Filter: TODO - confirm against the live GitHub Projects filter UI.
  GitHub Projects view filters are traditionally AND-only (space-separated
  qualifiers, same as GitHub search syntax) - a true OR between "has
  assignee" and "has review requested" may not be expressible as a single
  filter string. Options if so: (a) check whether GitHub has since added
  comma/OR syntax across qualifiers, (b) split into two side-by-side views,
  or (c) pick whichever single condition matters most.
- One view spanning all repos - NOT duplicated per-repo.
