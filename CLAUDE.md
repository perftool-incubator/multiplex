# Multiplex - Parameter Expansion Engine

## Purpose
Multiplex translates multi-value benchmark parameters into single-value test matrices. Given a set of parameters with multiple possible values, it produces all valid combinations (the Cartesian product), respecting parameter roles and constraints. Output feeds into rickshaw-run as `bench-params.json`.

## Language
Python 3 — single main file `multiplex.py` (~710 lines), no dependencies beyond `jsonschema`.

## Key Files
| File | Purpose |
|------|---------|
| `multiplex.py` | Core parameter expansion logic and CLI entry point |
| `params` | Default CLI arguments file (read by argparse `fromfile_prefix_chars`) |
| `JSON/schema.json` | JSON schema for multi-value input validation |
| `JSON/req-schema.json` | JSON schema for requirements file validation |

## Key Functions
| Function | Purpose |
|----------|---------|
| `multiplex_sets()` | Main driver: expands all parameter sets |
| `multiplex_set()` | Expands one multi-value set into multiple single-value sets (Cartesian product via `itertools.product`) |
| `load_param_sets()` | Resolves `include`/`include-preset` references and a set's own `params` into one param list per set |
| `merge_param()` | Shared by `merge_param_include()`/`merge_param_own()`: adds a param to a set, replacing an existing same-arg/role/id param if `replace` is True, skipping it otherwise (repeatable args always add instead, via `merge_repeatable_param()`) |
| `merge_param_include()` | `merge_param(..., replace=False)` — matches `include`/`include-preset` semantics (an existing same-arg/role/id param wins, this one is skipped with a warning) |
| `merge_param_own()` | `merge_param(..., replace=True)` — matches a set's own `params` semantics (this entry replaces an existing same-arg/role/id param) |
| `merge_repeatable_param()` | Shared by `merge_param()`: if the arg is repeatable, adds it (unless an exact duplicate is already present) and reports the case as handled; returns `False` for a non-repeatable arg so the caller applies its own replace-or-skip semantics |
| `exact_duplicate_exists()` | Checks for a byte-for-byte identical (arg, vals, role, id) entry — used by both merge functions and essentials to avoid appending a repeatable arg that's already present |
| `override_presets()` | Applies defaults, essentials, and named presets from requirements |
| `is_repeatable()` | Checks whether an arg was declared `repeatable` by a validation group |
| `transform_param_val()` | Applies validation regex, unit conversion, and regex transformation |
| `validate_schema()` | Validates input JSON against schema |

## Repeatable args
A validation group in the requirements file can set `"repeatable": true` (alongside `args`/`vals`) to declare that its args may legitimately be specified more than once within a single set — e.g. multiple independent setup/cleanup commands. Repeatable args are always unioned: `merge_param_include()`/`merge_param_own()` never collapse or replace them, only skipping an exact `(arg, vals, role, id)` duplicate via `exact_duplicate_exists()`. `override_presets()` applies each essential via `merge_param_own()` directly, so essentials get the identical repeatable-vs-replace treatment. An arg not declared repeatable keeps the original single-occurrence contract: duplicates from a set's own `params` or from a `defaults`/`essentials` preset collapse to the *last* one processed, matching the same last-group-wins convention used for `validation_dict`/`convert_dict`/`transform_dict`/`repeatable_args` itself — if multiple essentials (or multiple defaults) share the same non-repeatable `(arg, role, id)`, a warning is logged (once per run, not once per set) but the last one still takes effect. `enabled: no` on an essential/default excludes it entirely before this matching happens, so a disabled one can never claim an identity that a later, actually-enabled one needs. A duplicate arriving via `include`/`include-preset` instead collapses to the *first* one (unchanged, pre-existing semantics — a set's own `params` is what's meant to override an included value) but still logs the same kind of warning, since two *included* sources sharing an identity is equally likely to be a mistake.

A repeatable arg's *individual occurrences* must each be single-valued — `merge_repeatable_param()` rejects (exits `EC_VALIDATIONS_FAIL`) an occurrence whose `vals` array has more than one value. Multiple separate occurrences (each with one value) are the only supported shape; sweeping a repeatable arg's own values has no defined interaction with the Cartesian-product engine yet and is rejected outright rather than silently cross-multiplying against other occurrences.

Matching for essentials (and everywhere else in this file) is by the full `(arg, role, id)` tuple, not `arg` alone — an essential that omits `role`/`id` defaults to `client`/`1` and will *not* override an existing param with an explicit different role; the two coexist as distinct entries. This is deliberate: a role/id, when specified, is meant to scope what happens to that role/id only, and should not influence a different one.

If the same arg is declared in more than one validation group, the last group processed wins — the same conflict-resolution rule already used for `validation_dict`/`convert_dict`/`transform_dict`.

## Exit Codes
| Code | Constant | Meaning |
|------|----------|---------|
| 0 | `EC_SUCCESS` | Success |
| 1 | `EC_SCHEMA_FAIL` | Input JSON schema validation failed |
| 2 | `EC_JSON_FAIL` | JSON file loading failed |
| 3 | `EC_REQUIREMENTS_FAIL` | Requirements file loading failed |
| 4 | `EC_VALIDATIONS_FAIL` | Parameter validation failed |
| 5 | `EC_REQ_SCHEMA_FAIL` | Requirements JSON schema validation failed |
| 6 | `EC_EMPTY_SET_FAIL` | Empty param set after preset override |

## Input/Output
- **Input**: JSON with `global-options` and `sets` arrays; params use `arg` and `vals` (multi-value list) keys, optional `role` (client/server/all), `id`, `enabled`
- **Output**: JSON array of arrays; each inner array is one test iteration with single-value params using `arg`, `val`, and `role` keys
- **Requirements** (optional): Defines `presets` (defaults, essentials, named), `validations` (regex, and optionally `repeatable`), and `units` (conversion factors)

## Tests
Run from the project root with `pytest multiplex.py tests/*.py` (test files use hyphenated names like `test-json.py`, which pytest's default `test_*.py` discovery pattern won't find — the files must be passed explicitly, as CI's workflow does):
- `tests/test-json.py` — Parameter loading, multiplexing, Cartesian expansion, value conversion
- `tests/test-requirements.py` — Validation regex, presets, unit conversion, preset precedence
- `tests/test-schema.py` — Schema validation for valid and invalid inputs
- 60+ JSON fixtures in `tests/JSON/`

## Conventions
- 4-space indentation, PEP 8 naming
- Module-level dicts for state: `validation_dict`, `convert_dict`, `transform_dict`, `presets_dict`, `repeatable_args`
- Uses Python `logging` module for debug/info/warning/error output
