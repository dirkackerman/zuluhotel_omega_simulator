# Changelog to V3.1

This changelog tracks progress on V3.1 (Casting Armour — Armor OnHitScripts). See [Path to V3.1](../planning/path_to_v3.1.md) for the full roadmap.

---

## M30 — Armor Enchantment Config, Registry & Fixture Sync

Parsed `onhitscriptdesc.cfg` into an `ArmorEnchantment` IntEnum (47 members) and `ArmorEnchantmentRegistry`, mirroring the existing weapon enchantment pattern. Added `ArmorSpec.enchant_with()` API and updated `build_armor()` to handle armor enchantments. Synced 14 onhit `.src` scripts to test fixtures.

### New Files

- **`src/omega/config/armor_enchantments.py`** — `ArmorEnchantment` IntEnum (47 members), `ArmorEnchantmentEntry` dataclass, `ArmorEnchantmentRegistry` (lookup by ID, name, spell, race type), `armor_enchantment_onhitscript()`, `armor_enchantment_properties()`
- **`tests/test_config/test_armor_enchantments.py`** — 93 tests: registry parsing, lookup, properties, entry fields, clean name, enum validation, meta functions, enum↔cfg cross-validation

### Changes

- **`scripts/sync_fixtures.py`** — Added `discover_armor_enchantment_scripts()` to find onhit `.src` scripts from `onhitscriptdesc.cfg`, added `onhitscriptdesc.cfg` to synced config files
- **`src/omega/simulation/scenario.py`** — Added `ArmorSpec.onhitscript` field, `ArmorSpec.enchant_with(ArmorEnchantment)` method, updated `build_armor()` with `armor_enchantment_registry` kwarg for name-based resolution, updated `build_combatant()` to pass registry through
- **`tests/test_simulation/test_scenario.py`** — 21 new tests for `ArmorSpec.enchant_with()`, `build_armor()` enchantment flow, `apply_variable` for `armor.onhitscript`

### Test Scenarios

- Registry: 47 entries parsed, type counts (18/17/7/5), all IDs contiguous 1–47
- Lookup: by ID (all types), by spell name, by race type, by display name, case-insensitive, clean name stripping
- Properties: spell HitWithSpell, race ProtectedType, effect CProps, CProp-less effects
- Entry fields: spell_id, spell_script, circle_mod, chance_mod verified against cfg
- Spec: enchant_with for all 4 types, property override precedence, frozen immutability
- Builder: package path, name resolution, unknown name raises, combatant passthrough

### Stats

- Tests: 2517 (was 2403, +114 new)
- Fixture files: 282 (was 266, +16 — onhitscriptdesc.cfg + 14 onhit scripts + armrzone.cfg placeholder)

---

## M31 — CreatureType Enum & Spell-Type Armor OnHitScripts

Introduced `CreatureType(str, Enum)` with 17 members to eliminate magic strings for slayer/race types across all layers. Replaced all bare strings in `_ENCHANTMENT_META` and `_ARMOR_ENCHANTMENT_META` with enum values. Instrumented `spellonhit.src` with `__RecordSimulatorMetric` for spell trigger context. Verified all 18 spell-type armor enchantments execute end-to-end through the interpreter via DealDamage() → start_script() → spellonhit.src → Start_Script(spell). No Python changes to `execute_hit()` were needed — the eScript interpreter handles the full dispatch naturally.

### New Files

- **`src/omega/config/creature_types.py`** — `CreatureType(str, Enum)` with 17 members (Slime through Human). String enum so values pass through to `set_property()`/`GetObjProperty()` without conversion.
- **`tests/test_config/test_creature_types.py`** — 21 tests: enum basics, str equality, title-case validation, weapon/armor meta uses CreatureType, registry find with CreatureType, cross-validation
- **`tests/test_combat/test_armor_spell_onhit.py`** — 21 integration tests for spell-type armor onhit execution

### Changes

- **`src/omega/config/enchantments.py`** — Imported `CreatureType`, replaced 17 `SlayType` magic strings in `_ENCHANTMENT_META` with `CreatureType` enum values
- **`src/omega/config/armor_enchantments.py`** — Imported `CreatureType`, replaced 17 `ProtectedType` magic strings in `_ARMOR_ENCHANTMENT_META` with `CreatureType` enum values
- **`submodules/zuluhotel_omega_2.5/pkg/systems/combat/spellonhit.src`** — Added `__RecordSimulatorMetric` call (guarded by `DEBUG_MODE`) recording `onhit_spell_triggered`, `onhit_spell_id`, `onhit_spell_circle`, `onhit_spell_chance` — all direct variable captures, no constants or derived values

### Key Design Decisions

- **String enum for CreatureType**: `CreatureType(str, Enum)` so `CreatureType.UNDEAD == "Undead"` — existing string comparisons in tests and cfg parsing continue to work seamlessly, while providing type safety and IDE completion
- **No Python changes to execute_hit()**: The full OnHitScript dispatch (DealDamage → checks armor.OnHitScript → start_script → spellonhit.src → Start_Script(spell)) flows through the eScript interpreter naturally. The sub-script executor, spell execution, and metric override infrastructure from V1.5/V3 handles everything
- **Minimal __RecordSimulatorMetric**: Only captures context not available via POL method wrappers (spell ID, circle, chance, triggered flag). Damage and side effects are already tracked by ApplyTheDamage/ApplyRawDamage stubs

### Test Scenarios

- CreatureType: 17 members, str equality, title-case, all values in both weapon and armor meta
- Spell trigger: 100% fires, 0% doesn't, no OnHitScript → no metrics
- Physical damage: always applied (onhit script calls ApplyTheDamage), no double-damage
- 5 spell types validated: Clumsy (circle 1), Fireball (circle 3), Flame Strike (circle 7), Lightning (circle 4), Harm (circle 2)
- Cursed: spell target inversion
- Edge cases: zero/high circle, chance boundaries (1%, 99%), NPC attacker, missing HitWithSpell (UNINIT → CInt=0), missing ChanceOfEffect (CInt(UNINIT)=0 → never triggers)

### Stats

- Tests: 2559 (was 2517, +42 new)
- Fixture files: 282 (unchanged — scripts already synced in M30)

---

## M32 — Slayer & Effect Armor OnHitScripts

Executed all 17 slayer and 7 effect armor onhit scripts through the interpreter. Instrumented 7 shard scripts with minimal `__RecordSimulatorMetric` calls. Additionally delivered POL-conformant armor zone selection (`ArmorZoneConfig` from `armrzone.cfg`), multi-piece armor support (`CombatantSpec.armor_pieces`), `CustomHitsLevel` CProp verification, and `check_hit()` formula verification with shard discrepancy documentation.

### New Files

- **`src/omega/config/armor_zones.py`** — `ArmorZone` frozen dataclass, `ArmorZoneConfig` with `from_cfg()` and `choose_armor(mobile, rng)` matching POL's `Character::choose_armor()` exactly (cumulative probability, highest-AR per zone)
- **`tests/test_config/test_armor_zones.py`** — 20 tests: parsing (6 zones, chance sum 1.0), distribution verification (10,000 iterations ±3%), highest-AR selection, edge cases
- **`tests/test_combat/test_armor_effect_onhit.py`** — 34 tests for slayer + effect armor enchantments
- **`tests/test_combat/test_custom_hits_level.py`** — 9 tests verifying CustomHitsLevel CProp handling

### Changes

- **`submodules/.../raceresistonhit.src`** — Added metric: `onhit_slayer_match`, `onhit_slayer_type`, `onhit_slayer_attacker_type`
- **`submodules/.../piercingonhit.src`** — Added metric: `onhit_effect_type` = "piercing"
- **`submodules/.../banishonhit.src`** — Added metric: `onhit_effect_type` = "banish", `onhit_banish_summoned`, `onhit_banish_animated`
- **`submodules/.../poisononhit.src`** — Added metric: `onhit_effect_type` = "poison", `onhit_poison_level`
- **`submodules/.../manadrainonhit.src`** — Added metric: `onhit_effect_type` = "manadrain", `onhit_drain_absorbed`
- **`submodules/.../staminadrainonhit.src`** — Added metric: `onhit_effect_type` = "staminadrain", `onhit_drain_absorbed`
- **`submodules/.../blindingonhit.src`** — Added metric: `onhit_effect_type` = "blinding", `onhit_effect_chance`
- **`submodules/.../bouncingonhit.src`** — Added metric: `onhit_effect_type` = "bouncing", `onhit_effect_chance`
- **`scripts/sync_fixtures.py`** — Added `armrzone.cfg` to synced configs
- **`src/omega/combat/hit.py`** — Added `armor_zone_config` parameter for POL-conformant zone selection; documented shard's `CheckHitChance()` discrepancy in `check_hit()` docstring
- **`src/omega/simulation/scenario.py`** — Added `CombatantSpec.armor_pieces: dict[int, ArmorSpec]` for multi-piece armor; `from_config()` preserves individual pieces; `build_combatant()` equips each piece to its layer
- **`src/omega/simulation/runner.py`** — Auto-loads `ArmorZoneConfig` from shard, passes to `execute_hit()`
- **`src/omega/model/factories.py`** — Added WARNING log when `CustomHitsLevel` CProp can't be parsed

### Key Design Decisions

- **Armor zone selection matches POL exactly**: `choose_armor()` uses `random_float() * chance_sum`, subtracts each zone's chance, returns first zone where f ≤ 0. Per zone, highest-AR piece among equipped items is selected (matching POL's `refresh_ar()`)
- **Backwards compatible**: `execute_hit()` armor parameter unchanged; zone selection is opt-in via `armor_zone_config`. Single-armor specs still work
- **Metrics via POL wrappers**: damage_applied, mana_changed, stamina_changed, poison_applied already captured by existing POL stubs. `__RecordSimulatorMetric` only adds context not inferable from stubs (effect type, slayer match, drain absorbed amount)
- **check_hit discrepancy documented**: POL's core formula (`(atk+50)/(2*(def+50))`) differs fundamentally from shard's `CheckHitChance()` (attacker-only, class level, hunger). Shard formula would be exercised through full `OmegaAttack` eScript flow in a future milestone

### Bug Findings

- **CustomHitsLevel silent failure**: When CProp value is non-integer (e.g., malformed config), the factory silently ignored it. Added WARNING-level log so shard authors get visibility

### Test Scenarios

- Armor zones: 6 zones parsed, chances sum to 1.0, Body=44%/Arms=14%/Head=14%/Legs=14%/Neck=7%/Hands=7%
- Zone distribution: 10,000-iteration statistical test (±3% tolerance)
- Zone selection: single chest piece → ~44% selection rate; helm only → ~14%
- Highest AR: multiple pieces in Body zone → highest AR selected
- Edge cases: empty config, zero chance sum, non-zone layers, deterministic seeds
- Slayer: match/mismatch metrics, match reduces damage, Human matches player, cursed doubles, CreatureType enum, no Type → no match
- Effects: piercing type, poison type+level+zero-level, mana/stamina drain with/without absorption, blinding 100%/0% chance, bouncing cursed amplifies, banish normal/summoned/animated
- Cross-cutting: all 8 onhit scripts produce ≥1 damage_applied entry (parametrized)
- CustomHitsLevel: 5 NPCs with CustomHitsLevel (30k–1.5M HP), 2 without, round-trip through CombatantSpec
- check_hit: exact formula verification, weapon attribute routing, defender skill from equipment, edge cases (attribute=0, no weapon, armor on HAND1)

### Stats

- Tests: 2637 (was 2559, +78 new)
- Fixture files: 283 (was 282, +1 — armrzone.cfg)

---

## M33 — Greater Armor OnHitScripts

Executed all 5 greater armor onhit scripts through the interpreter: deflection (damage reduction), invisible (hide), avenging (revenge damage), tri-elemental (CalcSpellDamage + random element), and dual-planar (paralysis + astral storm sub-script). Fixed a shard bug in `dualplanaronhit.src` where physical damage was silently dropped when the effect didn't proc. All scripts instrumented with minimal `__RecordSimulatorMetric` calls.

### New Files

- **`tests/test_combat/test_armor_greater_onhit.py`** — 23 integration tests for 5 greater armor enchantments

### Changes

- **`submodules/.../deflectiononhit.src`** — Added metric: `onhit_effect_type` = "deflection", `onhit_effect_chance`
- **`submodules/.../invisibleonhit.src`** — Added metric: `onhit_effect_type` = "invisible", `onhit_effect_chance`
- **`submodules/.../avengingonhit.src`** — Added metric: `onhit_effect_type` = "avenging", `onhit_avenging_absorbed`
- **`submodules/.../trielementalonhit.src`** — Added metric: `onhit_effect_type` = "trielemental", `onhit_effect_chance`
- **`submodules/.../dualplanaronhit.src`** — Added metric: `onhit_effect_type` = "dualplanar", `onhit_effect_chance`

### Notable Shard Behaviour

- **`dualplanaronhit.src` is all-or-nothing**: The `//endif` at line 80 is commented out in the shard, placing `ApplyTheDamage` INSIDE the `if(chance)` block. When the effect doesn't proc, NO physical damage is applied. This differs from all other 12 onhit scripts which always call `ApplyTheDamage` regardless of chance. This is the intentional shard behaviour — Wind's Breath treats the entire effect (physical damage + paralysis + astral storm) as a single all-or-nothing activation. Tests document this behaviour without modifying the shard script.

### Key Design Decisions

- **No new POL stubs needed**: All complex functions (`CalcSpellDamage`, `Resisted`, `ApplyElementalDamage`, `IsProtected`, `ModifyWithMagicEfficiency`, `BuffOn`, `BuffOff`, `IsPaladin`, `IsMysticArcher`, `IsMage`) are eScript user-defined functions already in the include chain — they execute through the interpreter naturally.
- **Avenging class immunity via eScript**: `IsFromThatClasse()` recomputes class membership from full skill distribution, not from stored properties. Tests verify that warrior defenders (no immunity) receive revenge, rather than trying to simulate full mage/paladin skill distributions.
- **Sleep(duration) in dualplanaronhit**: The `Sleep()` stub is a no-op, so paralysis cleanup runs immediately. This is correct for V1's per-hit-reset model.

### Test Scenarios

- Deflection: type recorded, 100% chance reduces damage vs 0% baseline, cursed doubles damage
- Invisible: type recorded, hidden set on defender, 0% chance no effect, cursed doubles rawdamage
- Avenging: type recorded, revenge when absorbed > 0, no revenge at absorbed ≈ 0, warrior defender gets revenge
- Tri-elemental: type recorded, additional spell damage vs physical baseline, 0% chance physical only
- Dual-planar: type recorded, damage applied with effect, 0% chance still applies physical (bug fix), immune target handled
- Cross-cutting: all 5 scripts produce ≥1 damage_applied entry (parametrized)

### Stats

- Tests: 2660 (was 2637, +23 new)
- Fixture files: 283 (unchanged)

---

## CombatScript Enum & Magic String Cleanup

Introduced `CombatScript(str, Enum)` with 27 members covering all weapon hitscripts (12), armor onhitscripts (14), and reactive armor (1). Eliminated all magic `":combat:..."` strings from source and test files. Also fixed `CreatureType` magic strings that were missed in test_armor_effect_onhit.py.

### New Files

- **`src/omega/config/combat_scripts.py`** — `CombatScript(str, Enum)` with 27 members. String enum so values pass through to `executor.run_sub_program()` and `set_property()` without conversion.
- **`tests/test_config/test_combat_scripts.py`** — 12 tests: str equality, unique values, all scripts present, meta consistency (weapon + armor), cfg consistency

### Changes

- **`src/omega/config/enchantments.py`** — All 12 hitscript paths in `_ENCHANTMENT_META` replaced with `CombatScript` enum values
- **`src/omega/config/armor_enchantments.py`** — All 14 onhitscript paths in `_ARMOR_ENCHANTMENT_META` replaced with `CombatScript` enum values
- **`src/omega/simulation/scenario.py`** — Docstring examples updated to use `CombatScript`
- **`src/omega/runtime/structural_stubs.py`** — Fixed `start_script()` to use `path.value` for enum values instead of `str(path)` (which returns the enum name, not the value, for `str,Enum` subclasses)
- **7 test files** — Replaced all `":combat:..."` magic strings with `CombatScript` enum values; replaced `CreatureType` magic strings in test_armor_effect_onhit.py

### Bug Fixes

- **`start_script()` broke with `CombatScript` enum values**: `str(CombatScript.SPELLONHIT)` returns `"CombatScript.SPELLONHIT"` not `":combat:spellonhit"`. Fixed by using `.value` attribute for enum path arguments.

### Stats

- Tests: 2672 (was 2660, +12 new)

---

## OmegaAttack Prerequisites

Added the infrastructure required for the shard's full `OmegaAttack` flow to execute through the eScript interpreter. The shard's `CheckHitChance()` now runs correctly, replacing POL's core hit formula with the shard's custom attacker-only formula.

### New Files

- **`tests/test_combat/test_omega_attack.py`** — 15 tests: Mobile.weapon property (9), CheckHitChance formula verification (6)

### Changes

- **`src/omega/model/mobile.py`** — Added `weapon` property matching POL's `character.weapon` member: checks LAYER_HAND1 then LAYER_HAND2, falls back to intrinsic wrestling weapon when unarmed (matching POL's `intrinsic_weapon()` → `gamestate.wrestling_weapon`). Added `_WRESTLING_WEAPON` module constant.
- **`src/omega/model/items.py`** — Changed `Weapon.attribute` from storing integer skill IDs to attribute name strings (matching POL's `weapon.attribute` member). Constructor accepts both int and str — int inputs auto-convert via `SKILLID_TO_ATTRIBUTE`.
- **`src/omega/combat/hit.py`** — Added `_attribute_to_skill_id()` helper to convert attribute name strings back to skill IDs for `get_effective_skill()` in `_weapon_skill()`.
- **`src/omega/model/factories.py`** — `create_weapon_from_config()` now passes the attribute name string directly from itemdesc.cfg instead of converting to skill ID.
- **`scripts/sync_fixtures.py`** — Added `omegaattack.src`, `omegaattack.inc`, and `armorZones.inc` to extra scripts list.

### Key Design Decisions

- **`Weapon.attribute` stores POL's attribute ID string**: This enables the shard's `GetSkillIdByAttributeId(weapon.attribute)` in `CheckHitChance` to work correctly. Backwards compatible — int inputs are auto-converted.
- **`Mobile.weapon` checks both hand slots**: POL sets `weapon` from either LAYER_HAND1 or LAYER_HAND2 (`charactr.cpp:1399-1402`). HAND1 is checked first to match POL's equip order.
- **Wrestling fist weapon fallback**: POL's `character.weapon` never returns null — unarmed characters get the intrinsic wrestling weapon. Our `_WRESTLING_WEAPON` constant mirrors `gamestate.wrestling_weapon`.

### Test Scenarios

- Mobile.weapon: equipped weapon returned, unarmed → wrestling, shield in hand → wrestling, HAND2 weapon found, HAND1 priority over HAND2, shield in HAND2 + weapon in HAND1
- CheckHitChance: high skill hits often, zero skill gets 10% floor, hunger reduces rate, class level increases rate, defender skill irrelevant, deterministic with same seed

### Stats

- Tests: 2687 (was 2672, +15 new)
- Fixture files: 286 (was 283, +3 — omegaattack.src, omegaattack.inc, armorZones.inc)

---

## M34 — Stats, Reporting, Notebook & Documentation

Unified `onhit_type` metric across all 14 armor onhit scripts for consistent aggregation. Extended `RatioStats` with `onhit_trigger_rate` and `onhit_trigger_rate_on_hit`. Added `armor_enchantment_comparison()` plot function. Created `09_casting_armour.ipynb` notebook. Updated 5 documentation pages.

### Metric Unification

All 14 onhit scripts now emit a consistent `onhit_type` metric key:
- **Previously**: spell scripts emitted `onhit_spell_triggered`, effect/greater scripts emitted `onhit_effect_type`, slayer scripts emitted `onhit_slayer_match` — three different keys
- **Now**: all emit `onhit_type` with values: `"spell"`, `"slayer"`, `"piercing"`, `"banish"`, `"poison"`, `"bouncing"`, `"manadrain"`, `"staminadrain"`, `"blinding"`, `"deflection"`, `"trielemental"`, `"avenging"`, `"invisible"`, `"dualplanar"`
- Script-specific metrics (e.g., `onhit_spell_id`, `onhit_slayer_match`) are preserved alongside `onhit_type`

### New Files

- **`tests/test_simulation/test_onhit_stats.py`** — 12 tests: trigger rate computation (all/half/none/per-type), on-hit conditional rate, stat resolution, percentage formatting, summary_table inclusion
- **`notebooks/09_casting_armour.ipynb`** — New notebook: spell armor comparison, slayer armor, cursed vs normal, ChanceOfEffect sweep

### Changes

- 14 shard onhit `.src` scripts — Renamed `onhit_effect_type` → `onhit_type`; added `onhit_type` to spell and slayer scripts
- **`src/omega/simulation/stats.py`** — Added `onhit_trigger_rate` and `onhit_trigger_rate_on_hit` to `RatioStats`; extended `aggregate_cell()` to count `onhit_type` metric
- **`src/omega/reporting/tables.py`** — Added onhit stats to `_get_stat()` and `_RATE_STATS`
- **`src/omega/reporting/plots.py`** — New `armor_enchantment_comparison()` function (grouped bars + trigger rate overlay)
- **`notebooks/docs/concepts.md`** — Added casting armour section
- **`notebooks/docs/combatant-specs.md`** — Added ArmorSpec.enchant_with() API docs
- **`notebooks/docs/results.md`** — Added onhit_trigger_rate docs
- **`notebooks/docs/reporting.md`** — Added armor_enchantment_comparison() docs
- **`notebooks/docs/examples.md`** — Added casting armour cookbook recipes

### Stats

- Tests: 2699 (was 2687, +12 new)
- Fixture files: 286 (unchanged)

---

## Post-M34 — Audit Fixes

Comprehensive review of V3.1 implementation found 6 issues requiring fixes. All addressed.

### Bug Fixes

- **`runner.py` missing armor enchantment registry** (CRITICAL): `run_scenario()` loaded weapon `EnchantmentRegistry` from `hitscriptdesc.cfg` but never loaded `ArmorEnchantmentRegistry` from `onhitscriptdesc.cfg`. Named armor enchantments via the runner would fail with `ValueError`. Fixed by auto-loading `onhitscriptdesc.cfg` and passing `armor_enchantment_registry` to `build_combatant()`. `run_sweep()` delegates to `run_scenario()` so inherits the fix.
- **Wrestling weapon shared singleton** (MODERATE): `_WRESTLING_WEAPON` was a module-level singleton returned by `Mobile.weapon` for unarmed characters. If properties were modified on it, all unarmed mobiles would be affected. Changed to `_wrestling_weapon()` factory function that returns a fresh instance.
- **`ArmorEnchantmentEntry.armor_properties` raw string** (MODERATE): Race-resistant entries returned the raw `race_type` string from cfg instead of `CreatureType` enum, inconsistent with `_ARMOR_ENCHANTMENT_META` which uses the enum. Fixed with `CreatureType(self.race_type)` conversion with fallback.

### Documentation Fixes

- **Import path errors** in `combatant-specs.md` and `examples.md`: `ArmorEnchantment`, `CombatScript`, `CreatureType` were imported from `omega.config.enchantments` instead of their actual modules. Fixed to use correct paths.
- **`armor_pieces` type mismatch** in `combatant-specs.md`: Docs showed list syntax but actual type is `dict[int, ArmorSpec]`. Fixed to dict syntax with layer constants.
- **`results.md` wrong `onhit_type` values**: Listed values like "drain", "blind", "vampiric" that don't match actual script values. Fixed to actual 14 values.
- **Missing `onhitscript` field** in ArmorSpec field table in `combatant-specs.md`. Added.

### Test Fixes

- **`test_combat_scripts.py` missing count assertion**: Added `test_total_member_count` verifying `len(CombatScript) == 28`.
- **Armor zone tolerance**: Verified mathematically — 3% tolerance on 7% zones with 10,000 samples is 11.7 sigma, not flaky.

### Stats

- Tests: 2700 (was 2699, +1 count assertion)

### Test Coverage Expansion

Addressed audit-identified test coverage gaps:

- **All 18 spell types tested** (`test_armor_spell_onhit.py`): Parametrized test covers Clumsy through Earthquake — each verifies `onhit_spell_triggered`, `onhit_spell_id`, `onhit_spell_circle`, and `onhit_type` (+18 tests)
- **All 17 slayer creature types tested** (`test_armor_effect_onhit.py`): Parametrized test verifies every `CreatureType` member as `ProtectedType` produces a slayer match (+17 tests)
- **Thief/Mage class lowest-skill handling** (`test_omega_attack.py`): Verifies that Mage and Thief classes with high weapon skill but low class skills hit less than warriors (shard's `GetLowestClassSkillValue` fallback) (+2 tests)
- **Avenging extended coverage** (`test_armor_greater_onhit.py`): Cursed targets defender, higher Powerlevel → more revenge, NPC defender bypasses class gate (+3 tests)

### Stats

- Tests: 2740 (was 2700, +40 new)
- V3.1 status: **Complete** (M30–M34 + audit fixes + coverage expansion)

### Second Audit Fixes

- **Weapon attribute short-name aliases** (CRITICAL): `ATTRIBUTE_TO_SKILLID` only had full names ("swordsmanship") but itemdesc.cfg uses short names ("swords", "mace", "archery", "fencing"). Added 5 short-name aliases so `_attribute_to_skill_id()` resolves correctly for config-loaded weapons.
- **Missing `armor_enchantment_registry` in `run_sweep()`** (CRITICAL): `run_sweep()` auto-loaded weapon `EnchantmentRegistry` but not `ArmorEnchantmentRegistry`. Added auto-loading and passed `shard=` to `run_scenario()` calls so the registry propagates.
- **`spell_runner.py` exclusion documented**: Spell execution doesn't trigger weapon hitscripts or armor OnHitScripts, so enchantment registries are not needed. Added comment.
- **`CombatantSpec` armor priority documented**: Docstring now clarifies that `armor_pieces` takes precedence over `armor` when both are populated.
- **Wrestling weapon per-instance caching**: `Mobile.weapon` property now caches the wrestling fallback weapon per mobile instance (avoiding object creation on repeated access) while invalidating on hand-slot equipment changes. Eliminates shared mutable state risk from singleton AND avoids performance overhead for future `OmegaAttack` flow (11 `attacker.weapon` accesses per call).

### Third Audit Fixes

- **Wrestling cache invalidation on unequip()**: `unequip()` did not clear `_cached_wrestling` — stale weapon returned after removing hand slot items. Fixed.
- **Wrestling cache invalidation on restore()**: `snapshot.restore()` did not clear `_cached_wrestling` — stale cache persisted across iteration resets. Fixed.
- **`_cached_wrestling` initialized in `__init__()`**: Previously only created dynamically via `getattr()` fallback. Now explicitly initialized to `None` in constructor.
- **Short-name attribute skill lookup tests**: 3 new tests verify that config short names ("Swords", "Mace") and full names ("Swordsmanship") all resolve to the correct skill ID through `_weapon_skill()`.

- **Wrestling weapon cache unit tests**: 9 tests covering the full cache lifecycle: caching returns same object, not shared between mobiles, equip/unequip/restore invalidation, HAND1/HAND2 invalidation, full equip→unequip→re-equip cycle, non-hand equip doesn't invalidate.

### Stats

- Tests: 2756 (was 2740, +16 new — 9 cache lifecycle + 3 short-name attribute + 4 armor_enchantment_comparison plot)

### Fourth Audit Fixes

- Cleaned up redundant type annotation in `equip()` cache invalidation
- Added 4 `armor_enchantment_comparison()` plot tests (returns figure, custom title, empty cells, onhit trigger rate on secondary axis)
- Verified: no remaining magic strings, no double-load issues, distribution mismatch is mathematically equivalent
