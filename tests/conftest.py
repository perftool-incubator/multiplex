import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import multiplex

# validation_dict/convert_dict/transform_dict/repeatable_args are all
# populated together, in one pass, by create_validation_dict() -- module-
# level state that accumulates across the whole test session. Reset all
# four before and after every test so a test that calls
# create_validation_dict() (directly, or indirectly via apply_flat_params())
# can't leak validation patterns into a later test that relies on
# validation_dict staying empty (param_validated()'s "no validation_dict
# means no validation enforced" bypass only applies when it's genuinely
# empty). Shared here (rather than duplicated per test file) since it
# applies regardless of which test module is exercising multiplex.py.
@pytest.fixture(autouse=True)
def reset_repeatable_args():
    multiplex.repeatable_args = {}
    multiplex.validation_dict = {}
    multiplex.convert_dict = {}
    multiplex.transform_dict = {}
    yield
    multiplex.repeatable_args = {}
    multiplex.validation_dict = {}
    multiplex.convert_dict = {}
    multiplex.transform_dict = {}


# opt-in (not autouse) since most tests intentionally rely on
# multiplex.presets_dict accumulating across the session (e.g.
# test_load_presets's own assertion that it starts empty depends on
# nothing else having touched it yet); tests that set presets_dict
# directly to exercise override_presets() in isolation can request this
# to guarantee cleanup even if an assertion fails partway through.
# Cleared both before and after the yield: clearing only after depends on
# every requesting test reassigning presets_dict wholesale rather than
# mutating it in place, which happens to be true today but isn't
# guaranteed under a different test order or a future in-place-mutating
# test.
@pytest.fixture
def reset_presets_dict():
    multiplex.presets_dict = {}
    yield
    multiplex.presets_dict = {}
