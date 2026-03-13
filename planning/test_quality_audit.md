# Test Quality & Coverage Audit — Shortcomings and Gaps

**Date**: 2025-03-13
**Scope**: Systematic review of test breadth, POL conformance, type system correctness, and coverage gaps across the entire test suite.
**Methodology**: Six audit areas examined: 1-based indexing, POL stub return values, type coercion, control flow, struct/array member access, config parsing.

---

## Executive Summary

The test suite (2196 tests, 0 failures) is strong on the combat-path happy path but has systematic gaps in three areas:

1. **Array return types from stubs** — Many stubs return Python `list` instead of `EArray`, breaking 1-based indexing when eScript code indexes into returned values.
2. **UNINIT edge cases in the interpreter** — Comparisons, logical operators, and arithmetic with UNINIT are correct in implementation but have almost no tests. A regression here would silently break shard execution.
3. **POL stub return type conformance** — Several stubs return Python `bool`, `None`, or mixed types where POL returns `int` (1/0) or ERROR objects.

**Estimated gap**: ~120 additional tests needed across all areas.

---

## Area 1: 1-Based Indexing Consistency

### What Works (Tested)
- `EArray.get(index)` / `EArray.set(index)` — 1-based, out-of-bounds returns UNINIT
- `_get_index()` for strings — 1-based character access
- `_get_index()` for Python lists — 1-based conversion (`idx - 1`)
- `_set_index()` for EArray and Python lists — 1-based with auto-extend
- `Find()` built-in — returns 1-based position, 0 for not found
- `SubStr()` built-in — 1-based start position
- String slicing `str[start, length]` — 1-based start, second arg is LENGTH

### Systematic Gap: Stubs Returning Python `list` Instead of `EArray`

When a POL stub returns a Python `list`, eScript code that indexes into the result will use `_get_index()` on a list, which does 1-based conversion. This *works* because `_get_index` handles plain lists with 1-based conversion. However, the inconsistency means:
- `TypeOf(result)` returns "Array" for both `list` and `EArray` (correct)
- `.append()` method dispatch works on `EArray` but not `list` (method call falls through to `getattr`)
- `.size()` method works on `EArray` but not `list`

**Stubs returning Python `list` (should be `EArray`):**

| Stub | File | Returns |
|---|---|---|
| `SplitWords()` | basic_stubs.py | `list[str]` |
| `ListEquippedItems()` | object_stubs.py | `list[Any]` |
| `GetConfigStringArray()` | structural_stubs.py | `list[str]` |
| `GetConfigStringKeys()` | structural_stubs.py | `list[str]` |
| `ListHostiles()` | structural_stubs.py | `list[]` |
| `ListMobilesNearLocationEx()` | structural_stubs.py | `list[Any]` |
| `ListMobilesNearLocation()` | structural_stubs.py | `list[Any]` |

**Stubs correctly returning `EArray`:**
| Stub | File |
|---|---|
| `ListItemsNearLocation()` | structural_stubs.py |
| `ListItemsNearLocationOfType()` | structural_stubs.py |

**Missing tests:**
1. `SplitWords("a b c")[2]` should return `"b"` (1-based) — no test for indexing the result
2. `ListEquippedItems(mob)[1]` should return first item — no test for indexing the result
3. `ListMobilesNearLocationEx(...)[1]` should return first mobile — no test
4. `.size()` and `.append()` on stub-returned arrays — no tests

**Recommended action**: Convert all array-returning stubs to return `EArray`. Add tests that index into, call `.size()` on, and iterate over returned arrays.

---

## Area 2: POL Stub Return Value Conformance

### Critical Return Type Issues

#### 2.1 Boolean Returns Where POL Returns Integer

POL functions return `int` (1/0), not booleans. While Python `bool` is a subclass of `int`, eScript code doing `if (result == 1)` will behave correctly, but `TypeOf(result)` would return "Integer" for both — so this is mostly cosmetic. However, explicit `is True` checks in tests could mask issues.

**Stubs returning Python `bool` directly:**

| Stub | Returns | Should Return |
|---|---|---|
| `_GuildStub.IsEnemyGuild()` | `False` | `0` |
| `_GuildStub.IsAllyGuild()` | `False` | `0` |
| `is_registered()` (internal) | `True`/`False` | N/A (not exposed to eScript) |

**Missing tests**: No test verifies `FindGuild(id).IsEnemyGuild(other)` returns `0` (integer), not `False` (bool).

#### 2.2 Mixed Return Types (Success vs Error)

| Stub | Success | Error | POL Behavior | Issue |
|---|---|---|---|---|
| `HealDamage()` | `1` (int) | `None` | Returns `1` always or ERROR | `None` should be `0` or EError |
| `GetEquipmentByLayer()` | Item | `None` | Item or ERROR | `None` should be EError |
| `ListEquippedItems()` | `list` | `[]` | Array or ERROR | `[]` is acceptable but type should be EArray |
| `DestroyItem()` | `1` | `None` | `1` or ERROR | `None` should be `0` or EError |
| `ConsumeMana()` | `1` | `0` | `1` or `0` | Correct |

**Missing tests**: No test checks what eScript code sees when `GetEquipmentByLayer()` returns `None` — does `if (result)` correctly evaluate to false? (Yes, but untested.)

#### 2.3 Stubs That Always Succeed (No Error Path)

| Stub | Always Returns | POL Returns |
|---|---|---|
| `ConsumeReagents()` | `1` | `1` (success) or `0` (missing reagents) |
| `FindGuild()` | `_GuildStub` | Guild or ERROR |
| `CheckLineOfSight()` | `1` | `1` or `0` |
| `CheckLosAt()` | `1` | `1` or `0` |
| `Distance()` | `1` | Actual distance (int) |

These are acceptable simulation simplifications, but should be documented and tests should verify the exact return values.

**Missing tests**: 11 stubs have no tests at all (see Section 2.4).

#### 2.4 Stubs With Zero Test Coverage

| Stub | Module | Type | Impact |
|---|---|---|---|
| `PlaySoundEffectPrivate()` | uo | No-op | None |
| `PlayMovingEffect()` | uo | No-op | None |
| `PlayMovingEffectEx()` | uo | No-op | None |
| `PlayObjectCenteredEffect()` | uo | No-op | None |
| `PlayObjectCenteredEffectEx()` | uo | No-op | None |
| `PlayStationaryEffect()` | uo | No-op | None |
| `PlayLightningBoltEffect()` | uo | No-op | None |
| `SpeakPowerWords()` | uo | No-op | None |
| `SendEvent()` | npc | No-op | None |
| `MoveObjectToLocation()` | uo | No-op | None |
| `RevokePrivilege()` | uo | No-op | None |

While these are all no-ops, they should have at minimum a "registered and callable" test to prevent regressions.

---

## Area 3: UNINIT Edge Cases

### 3.1 UNINIT in Comparisons (HIGH PRIORITY)

The `_eq()` function correctly handles UNINIT:
```python
def _eq(left, right):
    if left is None or left is UNINIT:
        return right is None or right is UNINIT  # UNINIT == UNINIT → True
    if right is None or right is UNINIT:
        return left is None or left is UNINIT    # anything == UNINIT → False
```

And comparisons correctly return `1`/`0`:
```python
return 1 if _eq(left, right) else 0
```

**Missing tests** (none of these have dedicated tests):

| Expression | Expected | Tested? |
|---|---|---|
| `UNINIT == 0` | `0` (false) | No |
| `UNINIT == ""` | `0` (false) | No |
| `UNINIT != 0` | `1` (true) | No |
| `UNINIT < 5` | Behavior undefined — needs POL verification | No |
| `UNINIT > 0` | Behavior undefined — needs POL verification | No |
| `UNINIT == UNINIT` | `1` (true) | Yes (in test_types.py) |
| `0 == UNINIT` | `0` (false) | No |
| `"" == UNINIT` | `0` (false) | No |

**Risk**: The combat path uses patterns like `if (variable)` and `if (variable != 0)` extensively. If a variable is unexpectedly UNINIT, the behavior must match POL — otherwise damage calculations could silently produce wrong results.

### 3.2 UNINIT in Logical Operators (HIGH PRIORITY)

The evaluator handles `&&` and `||` with short-circuit evaluation:
```python
# Simplified from visitExpression
if op == "&&":
    if not is_truthy(left):
        return left   # short-circuit: returns UNINIT if left is UNINIT
    return right
if op == "||":
    if is_truthy(left):
        return left
    return right
```

**Missing tests:**

| Expression | Expected | Tested? |
|---|---|---|
| `UNINIT && 5` | `UNINIT` (short-circuit, falsy) | No |
| `UNINIT \|\| 5` | `5` (left falsy, return right) | No |
| `5 && UNINIT` | `UNINIT` (left truthy, return right) | No |
| `5 \|\| UNINIT` | `5` (short-circuit, truthy) | No |
| `!UNINIT` | `1` (UNINIT is falsy) | No |
| `UNINIT && UNINIT` | `UNINIT` | No |

**Risk**: Shard code frequently uses `if (obj && obj.property)` guards. If UNINIT short-circuit doesn't work correctly, the interpreter would try to access `.property` on UNINIT and fail.

### 3.3 UNINIT in Arithmetic (MEDIUM PRIORITY)

The `_to_number()` function handles UNINIT:
```python
def _to_number(value):
    if value is None or value is UNINIT:
        return 0
```

So `UNINIT + 5` = `0 + 5` = `5`. This is the correct POL behavior (UNINIT coerces to 0 in arithmetic).

**Missing tests**: No test explicitly verifies `UNINIT + 5 == 5`, `UNINIT * 3 == 0`, etc.

### 3.4 UNINIT Propagation in Member Access

```python
def _get_member(obj, name):
    if obj is None or obj is UNINIT:
        return UNINIT  # accessing .field on UNINIT returns UNINIT
```

This is correct and allows safe chained access patterns like `obj.field.subfield` when `obj` is UNINIT.

**Missing tests**: No test for `UNINIT.member` → `UNINIT`.

---

## Area 4: Bitwise Operators

### Implementation Status

| Operator | Symbol | Implemented | Tested |
|---|---|---|---|
| Bitwise AND | `&` | Yes | Yes (damage type flags) |
| Bitwise OR | `\|` | Yes | Yes (damage type flags) |
| Bitwise XOR | `^` | Yes | **No** |
| Bitwise NOT | `~` | Yes | **No** |
| Left shift | `<<` | Yes | **No** |
| Right shift | `>>` | Yes | **No** |

**Missing tests:**
- `0x01 ^ 0x03` — XOR
- `~0x01` — NOT (should return `-2` per two's complement)
- `1 << 8` — left shift (should return `256`)
- `256 >> 4` — right shift (should return `16`)
- Negative number bitwise: `-1 & 0xFF` — should return `255`
- Damage type flag combinations: `FIRE | EARTH` combined then checked with `& FIRE`

**Risk**: Damage type constants are bitflags (FIRE=0x01, AIR=0x02, etc.). The combat path uses `&` and `|` extensively for damage type checking. XOR and shifts are less common but may appear in future shard code.

---

## Area 5: Control Flow Gaps

### 5.1 Exit Statement — Completely Untested

`exit` raises `ExitSignal` which propagates to the program boundary. No tests exist for:
- `exit` from main program body
- `exit` from inside a function (should exit program, not just function)
- `exit` from inside a loop

**Risk**: Low for current combat path (exit not used in combat scripts), but any future expansion could hit this.

### 5.2 Case Statement — Fall-Through Not Supported

The current implementation returns immediately after the first matching case block. eScript/POL traditionally supports fall-through (execution continues to next case unless `break` is used).

```escript
case (x)
    1:
    2:
        Print("one or two");  // fall-through from case 1 to case 2
        break;
    default:
        Print("other");
endcase
```

Our implementation would only match case 1 and return from its (empty) block, never reaching the "one or two" print.

**Tests needed:**
- Multi-label case (case 1: case 2: ... endcase)
- Break in case block behavior
- Fall-through semantics (if POL supports it)

**Risk**: Medium — case statements appear in some shard scripts for class/skill dispatch.

### 5.3 For Loop — No Descending Support

`for i := 10 to 1` never executes (condition `i <= end` is immediately false). eScript may not support descending for loops (needs POL verification), but if it does, the `i += 1` hardcoding would be wrong.

**Tests needed:**
- `for i := 5 to 1` — verify it executes 0 times (not 5 times or infinite)
- Document whether this matches POL behavior

### 5.4 Foreach Modification Safety — Untested

The implementation materializes the iterable before looping (`items = _to_iterable(iterable)`), so modifying the array during iteration is safe. But no test verifies this.

**Tests needed:**
- Modify array during foreach — verify loop sees original values
- Append to array during foreach — verify no infinite loop

### 5.5 Loop Variable Scope Leakage — Untested

Loop variables leak into the enclosing scope (correct for eScript, which has no block-level scoping). No test verifies this.

**Tests needed:**
```escript
var sum := 0;
for i := 1 to 5
    sum := sum + i;
endfor
// i should be 5 here (last value before increment past end)
```

### 5.6 Return From Nested Loop — Untested

`return` inside a for loop inside a function should exit the function. The implementation handles this correctly (ReturnSignal propagates through BreakSignal/ContinueSignal handlers), but no explicit test exists.

### 5.7 Continue in Do-While and Repeat-Until — Untested

Continue in post-test loops should skip to the condition check. Implementation looks correct but has no tests.

---

## Area 6: Struct/Array Member Access Gaps

### 6.1 Missing `.insert()` Method on Arrays

`_call_method()` handles `append`, `shrink`, and `size` for EArray but not `insert`. The shard submodule uses `.insert()` in 20+ places (mostly crafting/admin scripts, not combat path), but it's used on arrays (`name.insert(1, lvlname)`) and dictionaries (`dict.insert(key, value)`).

**Current fixture scripts**: No `.insert()` calls in the combat path fixtures. Low immediate risk.

**Tests needed**: If `.insert()` is ever encountered on the combat path, it will silently return `None` (fall-through to "Unknown method call" warning).

### 6.2 Missing Array/Dict Methods

| Method | EArray | EDict | In Shard? |
|---|---|---|---|
| `.insert(idx, val)` / `.insert(key, val)` | Missing | Missing | Yes (non-combat) |
| `.reverse()` | Missing | N/A | Unknown |
| `.sort()` | Missing | N/A | Unknown |
| `.values()` | N/A | Missing | Unknown |
| `.copy()` | Missing | Missing | Unknown |
| `.clear()` | N/A | Missing | Unknown |

### 6.3 Method Call on UNINIT — Untested

`UNINIT.method()` falls through to the POL registry lookup, then logs a warning and returns `None`. This is safe but untested.

### 6.4 Chained Access on UNINIT — Untested

`UNINIT.field.subfield` should return UNINIT at each step (via `_get_member(UNINIT, name) → UNINIT`). Working correctly but untested.

---

## Area 7: Config Parsing Gaps

### 7.1 RuntimeConfigElement API Incompleteness

`ConfigElement` provides: `get()`, `get_int()`, `get_float()`, `get_all()`, `get_cprop()`
`RuntimeConfigElement` provides: `__getattr__()`, `__getitem__()` only

If eScript code calls a method like `elem.get_int("key")` on a `RuntimeConfigElement`, it would fail because the wrapper doesn't delegate these methods.

**Missing tests**: No test verifies `RuntimeConfigElement.get_int()` or `RuntimeConfigElement.get_all()`.

### 7.2 Config Value Type Coercion

Config values are stored as strings. When eScript reads `elem.AR`, it gets the string `"50"`, not the integer `50`. The shard code then uses `CInt()` to convert. This matches POL behavior, but:

**Missing tests**: No test verifies that `RuntimeConfigElement.__getattr__("AR")` returns `"50"` (string) for a config entry `AR 50`.

### 7.3 Config Key Case Sensitivity

- Element names: Case-insensitive lookup (fallback to lowercase)
- Property keys: Case-sensitive (no fallback)

POL behavior unknown. If POL treats property keys case-insensitively, our implementation would fail on `elem.ar` when the config says `AR`.

**Missing tests**: No test for property key case sensitivity.

### 7.4 Config Element Enumeration in eScript

`foreach elem in (configfile)` should iterate over all config elements. `RuntimeConfigFile` implements `__iter__()` which delegates to `ConfigFile.__iter__()`.

**Missing tests**: No integration test that iterates a config file in eScript code.

### 7.5 CProp Edge Cases

**Missing tests:**
- CProp with no type prefix (e.g., `CProp Name value` — no `i` or `s` prefix)
- CProp with empty value (e.g., `CProp Flag`)
- CProp access via `RuntimeConfigElement.__getattr__()`

---

## Area 8: Cross-Cutting Concerns

### 8.1 `_to_number()` vs `CInt()` Divergence

`_to_number("3.7")` → `3.7` (float — detects "." and parses as float)
`CInt("3.7")` → `3` (integer — POL's `strtol` behavior)

These are used in different code paths:
- Arithmetic expressions use `_to_number()` → preserves decimal
- Explicit `CInt()` calls use the stub → truncates

This is correct behavior (implicit coercion preserves precision, explicit CInt truncates), but the divergence could surprise developers.

**Missing tests**: No test comparing `"3.7" + 0` (implicit, should be `3.7`) vs `CInt("3.7") + 0` (explicit, should be `3`).

### 8.2 `ApplyRawDamage` on UNINIT Mobile

`ApplyRawDamage(UNINIT, 10)` raises `AttributeError` because UNINIT has no `.hp` attribute. This should be caught and return silently.

**Missing tests**: No test for `ApplyRawDamage` with UNINIT mobile (the stub should handle this gracefully).

### 8.3 `is_truthy()` Edge Cases

The truthiness function handles most types correctly, but:

| Value | `is_truthy()` | Tested? |
|---|---|---|
| `0` | `False` | Yes |
| `0.0` | `False` | Yes |
| `""` | `False` | Yes |
| `None` | `False` | Yes |
| `UNINIT` | `False` | Yes |
| `EArray([])` | `False` | Yes |
| `EError(...)` | `False` | Yes |
| `EStruct({})` | `True` | Yes |
| `EDict()` | `True` | Yes |
| `True` (Python bool) | `True` | No — `bool` check before `int` matters |
| `False` (Python bool) | `False` | No |

**Missing tests**: Python `True`/`False` values in `is_truthy()` context (matters because `bool` is subclass of `int`).

---

## Recommended Test Plan

### Priority 1 — UNINIT Consistency Tests (~25 tests)

These test the general principle, not just one case. Every UNINIT interaction in the interpreter should be verified:

```
UNINIT Comparisons:
  UNINIT == 0       → 0
  UNINIT == ""      → 0
  UNINIT != 0       → 1
  UNINIT == UNINIT  → 1 (existing)
  0 == UNINIT       → 0
  "" == UNINIT      → 0
  UNINIT < 5        → verify behavior
  UNINIT > 0        → verify behavior

UNINIT Logical:
  UNINIT && 5       → UNINIT
  UNINIT || 5       → 5
  5 && UNINIT       → UNINIT
  5 || UNINIT       → 5
  !UNINIT           → 1
  UNINIT && UNINIT  → UNINIT
  UNINIT || UNINIT  → UNINIT

UNINIT Arithmetic:
  UNINIT + 5        → 5
  UNINIT * 3        → 0
  UNINIT - 1        → -1
  UNINIT / 2        → 0
  5 + UNINIT        → 5

UNINIT Member/Index:
  UNINIT.field      → UNINIT
  UNINIT[1]         → UNINIT
  UNINIT.field.sub  → UNINIT
```

### Priority 2 — Array Return Type Conformance (~15 tests)

Ensure all array-returning stubs return EArray and that consumers can use eScript array methods on the result:

```
For each array-returning stub:
  result := StubFunction(...)
  result[1]         → correct first element (1-based)
  result.size()     → correct count
  TypeOf(result)    → "Array"
  foreach val in result → iterates correctly
```

### Priority 3 — Bitwise Operator Tests (~10 tests)

```
0x01 ^ 0x03       → 0x02
~0x01              → -2
1 << 8             → 256
256 >> 4           → 16
-1 & 0xFF          → 255
FIRE | EARTH       → 0x05
(FIRE | EARTH) & FIRE → 0x01
```

### Priority 4 — Control Flow Edge Cases (~15 tests)

```
Exit:
  exit from main          → program stops
  exit from function      → program stops (not just function)
  exit from nested loop   → program stops

Case:
  case with break         → exits case
  case with multiple labels → verify behavior
  case with identifier    → constant evaluation

For loop:
  for i := 5 to 1        → 0 iterations
  loop variable after loop → last value accessible

Foreach:
  modify array during foreach → original values

Continue in do-while/repeat-until → correct skip
Return from inside for loop → correct function exit
```

### Priority 5 — POL Stub Return Value Tests (~20 tests)

For each stub that has no tests:
```
RegisteredAndCallableTest:
  call_builtin(module, name, default_args) → not error
  verify return type matches documented POL behavior
```

For stubs with wrong return types:
```
HealDamage(None, 10)  → should return 0, not None
FindGuild(1).IsEnemyGuild(2) → should return 0 (int), not False (bool)
```

### Priority 6 — Config Access Tests (~15 tests)

```
RuntimeConfigElement:
  elem.AR for "AR 50"    → "50" (string)
  elem.ar (lowercase)    → verify behavior
  elem.Missing           → verify UNINIT or None

RuntimeConfigFile iteration:
  foreach elem in cfg    → yields elements

CProp edge cases:
  CProp with no prefix   → raw string
  CProp with empty value → empty string
```

### Priority 7 — Type Coercion Edge Cases (~10 tests)

```
"3.7" + 0    → 3.7 (implicit float conversion)
CInt("3.7")  → 3 (explicit truncation)
is_truthy(True)  → True (bool before int check)
is_truthy(False) → False
```

---

## Summary Table

| Area | Gap Count | Severity | Estimated Tests |
|---|---|---|---|
| UNINIT edge cases | 20+ untested scenarios | HIGH | ~25 |
| Array return types | 7 stubs returning `list` | HIGH | ~15 |
| Bitwise operators | 4 operators untested | MEDIUM | ~10 |
| Control flow | 7 untested scenarios | MEDIUM | ~15 |
| POL stub returns | 11 stubs with 0 tests + type issues | MEDIUM | ~20 |
| Config access | 6 untested scenarios | MEDIUM | ~15 |
| Type coercion | 4 edge cases | LOW | ~10 |
| Struct/array methods | `.insert()` missing | LOW (not on combat path) | ~5 |
| **Total** | | | **~115** |
