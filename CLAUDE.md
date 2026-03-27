# Multiplex - Parameter Expansion Engine

## Purpose
Multiplex translates multi-value benchmark parameters into single-value test matrices. Given a set of parameters with multiple possible values, it produces all valid combinations (the Cartesian product), respecting parameter roles and constraints. Output feeds into rickshaw-run as `bench-params.json`.

## Language
Python 3 — single main file `multiplex.py` (~510 lines), no dependencies beyond `jsonschema`.

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
| `load_param_sets()` | Resolves `include` references from global-options into sets |
| `override_presets()` | Applies defaults, essentials, and named presets from requirements |
| `transform_param_val()` | Applies validation regex, unit conversion, and regex transformation |
| `validate_schema()` | Validates input JSON against schema |

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
- **Requirements** (optional): Defines `presets` (defaults, essentials, named), `validations` (regex), and `units` (conversion factors)

## Tests
Run with `cd` to project root, then `pytest tests/`:
- `tests/test-json.py` — Parameter loading, multiplexing, Cartesian expansion, value conversion
- `tests/test-requirements.py` — Validation regex, presets, unit conversion, preset precedence
- `tests/test-schema.py` — Schema validation for valid and invalid inputs
- 60+ JSON fixtures in `tests/JSON/`

## Conventions
- 4-space indentation, PEP 8 naming
- Module-level dicts for state: `validation_dict`, `convert_dict`, `transform_dict`, `presets_dict`
- Uses Python `logging` module for debug/info/warning/error output
