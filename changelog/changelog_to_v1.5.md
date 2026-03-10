# Changelog to V1.5

This changelog tracks progress on V1.5 (Elemental & Enchanted Weapons). See [Path to V1.5](../planning/path_to_v1.5.md) for the full roadmap.

---

## M12 — Elemental Protection Stubs

**Summary**: Verified that the shard's elemental protection functions (`GetProtLevel`, `GetResultingElementalProt`, `IsImmunedFromThisDamageType`) execute correctly through the interpreter. Added missing infrastructure for the elemental damage path.

**Changes**:
- **Interpreter bug fix**: `case`/`break` — `break` inside a `case` branch was propagating as an unhandled `BreakSignal` instead of exiting the matched case. Fixed in `evaluator.py`.
- **Mobile model**: Added `hidden` (bool) and `master` (Any) attributes needed by `ApplyElementalDamageNoResist` in spelldata.inc.
- **Snapshot**: `hidden` is now captured/restored between iterations.
- **HealDamage stub**: New POL built-in stub (`vitals::HealDamage`) for the over-protection healing path (protection > 100% heals instead of damages). Records a `"heal"` side effect.
**Testing**:
- Verify `GetProtLevel` returns the correct property value for each of the 6 mapped elements (FIRE/AIR/EARTH/WATER/NECRO/HOLY) and returns 0 for unmapped elements (POISON, ACID, PHYSICAL, MAGIC, ASTRAL)
- Verify `GetResultingElementalProt` delegates to `GetProtLevel` (dead code after early return on line 645)
- Verify `IsImmunedFromThisDamageType` handles: full immunity, partial immunity (damage reduction), no immunity, and `DMGID_NO_RESIST` bypass
- Verify over-protection (>100%) path reaches `HealDamage` — heals instead of damages
- Verify `hidden` state is preserved across snapshot/restore cycles
- Confirm existing combat tests still pass (the `case`/`break` fix is a behavioral change)

**Key insight**: The protection functions are eScript user-defined functions in spelldata.inc/damages.inc (not POL built-ins). They're already in the parsed include chain (`hitscriptinc.inc → dotempmods.inc → spelldata.inc`). M12 was about verifying they work and filling infrastructure gaps.
