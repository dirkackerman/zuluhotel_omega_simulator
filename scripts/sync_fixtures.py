#!/usr/bin/env python3
"""Sync shard files into test fixtures.

Copies the minimal set of shard resources needed by tests into
``tests/fixtures/shard/``, preserving relative paths.  Large config
files (npcdesc.cfg, equip.cfg) are trimmed to only the templates
referenced by tests.

Usage::

    python scripts/sync_fixtures.py [--shard-root PATH] [--dry-run]
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHARD_ROOT = PROJECT_ROOT / "submodules" / "zuluhotel_omega_2.5"
FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "shard"

# NPC template names referenced in tests (test_cfg_parser, test_model_integration)
NPC_TEMPLATES_NEEDED = {
    "beckon",
    "dracoliche",
    "earthelementalsummons",
    "airelemental",
    "earthelemental",
    "nazgul",       # referenced in equip test
    "skeleton",     # representative undead for slayer tests
}

# Equipment template names referenced in tests
# Includes both directly referenced names AND equip templates used by needed NPCs
EQUIP_TEMPLATES_NEEDED = {
    "nazgul",           # nazgul equipment test (test_cfg_parser)
    "wisp",             # beckon NPC's Equip template
    "balron1",          # earthelementalsummons NPC's Equip template
    "airelemental",     # airelemental NPC's Equip template
    "earthelemental",   # earthelemental NPC's Equip template
    "dracoliche",       # dracoliche NPC's Equip template
}


def discover_include_tree(shard_root: Path) -> set[Path]:
    """Use the parser to discover all files in the mainhit.src include chain."""
    # Add project src to path so imports work
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

    from omega.parser import parse_with_includes
    from omega.shard import ShardData

    shard = ShardData.from_path(shard_root)
    trees = shard.parse_combat_scripts()
    return set(trees.keys())


def discover_enchantment_scripts(shard_root: Path) -> set[Path]:
    """Discover enchantment sub-scripts from hitscriptdesc.cfg and hardcoded paths.

    Parses hitscriptdesc.cfg to find all ``Hitscript`` values (e.g.,
    ``:combat:spellstrikescript``) and resolves them to ``.src`` files.
    Also includes the hardcoded ``reactivearmoronhit.src`` from
    hitscriptinc.inc.
    """
    scripts: set[Path] = set()

    # Hardcoded: reactive armor on-hit script (called directly in hitscriptinc.inc)
    combat_dir = shard_root / "pkg" / "systems" / "combat"
    reactive = combat_dir / "reactivearmoronhit.src"
    if reactive.exists():
        scripts.add(reactive.resolve())

    # Data-driven: parse hitscriptdesc.cfg for Hitscript values
    cfg_path = combat_dir / "config" / "hitscriptdesc.cfg"
    if not cfg_path.exists():
        return scripts

    text = cfg_path.read_text(encoding="utf-8", errors="replace")
    for match in re.finditer(r'^\s*Hitscript\s+(\S+)', text, re.MULTILINE):
        hitscript = match.group(1).strip()
        if hitscript.startswith(":"):
            # Resolve :combat:name → pkg/systems/combat/name.src
            parts = hitscript.lstrip(":").split(":", 1)
            if len(parts) == 2:
                pkg_name, file_name = parts
                # Map package name to directory
                pkg_dir = _find_package_dir(shard_root, pkg_name)
                if pkg_dir:
                    src = pkg_dir / f"{file_name}.src"
                    if src.exists():
                        scripts.add(src.resolve())

    return scripts


def _find_package_dir(shard_root: Path, pkg_name: str) -> Path | None:
    """Find a package directory by scanning pkg.cfg files."""
    pkg_root = shard_root / "pkg"
    if not pkg_root.exists():
        return None
    for cfg in pkg_root.rglob("pkg.cfg"):
        text = cfg.read_text(encoding="utf-8", errors="replace")
        name_match = re.search(r'^\s*Name\s+(\S+)', text, re.MULTILINE)
        if name_match and name_match.group(1).lower() == pkg_name.lower():
            return cfg.parent
    return None


def discover_package_cfgs(shard_root: Path) -> list[Path]:
    """Find all pkg.cfg files under the shard's pkg/ directory."""
    pkg_root = shard_root / "pkg"
    if not pkg_root.exists():
        return []
    return list(pkg_root.rglob("pkg.cfg"))


def trim_block_config(cfg_path: Path, needed_names: set[str]) -> str:
    """Extract only the blocks matching needed_names from a block config file.

    Handles the POL config format:
        BlockType name
        {
            ...
        }
    """
    text = cfg_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check if this line starts a block: "BlockType name" followed by "{"
        # Pattern: word(s) then a name, next non-empty line is "{"
        block_match = re.match(r'^(\w+)\s+(\S+)\s*$', stripped)
        if block_match:
            block_type = block_match.group(1)
            block_name = block_match.group(2).lower()

            # Look ahead for opening brace
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1

            if j < len(lines) and lines[j].strip() == "{":
                # Found a block — check if we need it
                if block_name in {n.lower() for n in needed_names}:
                    # Collect the entire block
                    block_lines = lines[i:j+1]  # header + brace
                    k = j + 1
                    depth = 1
                    while k < len(lines) and depth > 0:
                        if lines[k].strip() == "{":
                            depth += 1
                        elif lines[k].strip() == "}":
                            depth -= 1
                        block_lines.append(lines[k])
                        k += 1
                    result.extend(block_lines)
                    result.append("\n")
                    i = k
                    continue
                else:
                    # Skip this block entirely
                    k = j + 1
                    depth = 1
                    while k < len(lines) and depth > 0:
                        if lines[k].strip() == "{":
                            depth += 1
                        elif lines[k].strip() == "}":
                            depth -= 1
                        k += 1
                    i = k
                    continue

        i += 1

    return "".join(result)


def sync_fixtures(shard_root: Path, dry_run: bool = False) -> None:
    """Copy shard resources into the fixture directory."""
    if not shard_root.exists():
        print(f"ERROR: Shard root not found: {shard_root}")
        sys.exit(1)

    files_copied: list[tuple[Path, Path]] = []

    def copy_file(src: Path, dest: Path) -> None:
        if dry_run:
            print(f"  [dry-run] {src.relative_to(shard_root)} → {dest.relative_to(FIXTURE_DIR)}")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        files_copied.append((src, dest))

    def write_file(dest: Path, content: str, label: str) -> None:
        if dry_run:
            print(f"  [dry-run] {label} → {dest.relative_to(FIXTURE_DIR)} ({len(content)} bytes)")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
        files_copied.append((Path(label), dest))

    # 1. Discover transitive include tree from mainhit.src
    print("Discovering include tree from mainhit.src...")
    included_files = discover_include_tree(shard_root)
    print(f"  Found {len(included_files)} files in include chain")

    # 2. Copy all included files (preserving relative paths)
    print("\nCopying eScript source files...")
    for src_path in sorted(included_files):
        rel = src_path.relative_to(shard_root.resolve())
        dest = FIXTURE_DIR / rel
        copy_file(src_path, dest)

    # 2b. Discover and copy enchantment sub-scripts
    print("\nDiscovering enchantment sub-scripts from hitscriptdesc.cfg...")
    enchantment_scripts = discover_enchantment_scripts(shard_root)
    print(f"  Found {len(enchantment_scripts)} enchantment scripts")

    print("\nCopying enchantment scripts...")
    for src_path in sorted(enchantment_scripts):
        if src_path in included_files:
            continue  # Already copied as part of include tree
        rel = src_path.relative_to(shard_root.resolve())
        dest = FIXTURE_DIR / rel
        copy_file(src_path, dest)

    # 3. Copy all pkg.cfg files (needed by PackageResolver and ShardData)
    print("\nCopying pkg.cfg files...")
    pkg_cfgs = discover_package_cfgs(shard_root)
    for pkg_cfg in sorted(pkg_cfgs):
        rel = pkg_cfg.relative_to(shard_root)
        dest = FIXTURE_DIR / rel
        copy_file(pkg_cfg, dest)
    print(f"  Copied {len(pkg_cfgs)} pkg.cfg files")

    # 4. Copy config files
    print("\nCopying config files...")

    # combat.cfg — small, copy in full
    combat_cfg = shard_root / "config" / "combat.cfg"
    if combat_cfg.exists():
        copy_file(combat_cfg, FIXTURE_DIR / "config" / "combat.cfg")

    # npcdesc.cfg — trimmed to needed templates
    npcdesc_path = shard_root / "config" / "npcdesc.cfg"
    if npcdesc_path.exists():
        trimmed = trim_block_config(npcdesc_path, NPC_TEMPLATES_NEEDED)
        write_file(
            FIXTURE_DIR / "config" / "npcdesc.cfg",
            trimmed,
            "npcdesc.cfg (trimmed)",
        )

    # equip.cfg — trimmed to needed templates
    equip_path = shard_root / "config" / "equip.cfg"
    if equip_path.exists():
        trimmed = trim_block_config(equip_path, EQUIP_TEMPLATES_NEEDED)
        write_file(
            FIXTURE_DIR / "config" / "equip.cfg",
            trimmed,
            "equip.cfg (trimmed)",
        )

    # Package config files — copy in full
    pkg_configs = [
        "pkg/systems/combat/config/itemdesc.cfg",
        "pkg/systems/combat/config/settings.cfg",
        "pkg/systems/combat/config/hitscriptdesc.cfg",
    ]
    for rel_path in pkg_configs:
        src = shard_root / rel_path
        if src.exists():
            copy_file(src, FIXTURE_DIR / rel_path)

    # 5. Copy .em module files
    print("\nCopying .em module files...")
    em_dir = shard_root / "scripts" / "modules"
    if em_dir.exists():
        em_count = 0
        for em_file in sorted(em_dir.glob("*.em")):
            copy_file(em_file, FIXTURE_DIR / "scripts" / "modules" / em_file.name)
            em_count += 1
        print(f"  Copied {em_count} .em files")

    # Summary
    total_size = 0
    if not dry_run:
        for _, dest in files_copied:
            if dest.exists():
                total_size += dest.stat().st_size

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Summary:")
    print(f"  Files: {len(files_copied)}")
    if not dry_run:
        print(f"  Total size: {total_size / 1024:.1f} KB")
    print(f"  Destination: {FIXTURE_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync shard files into test fixtures")
    parser.add_argument(
        "--shard-root",
        type=Path,
        default=DEFAULT_SHARD_ROOT,
        help=f"Path to shard root (default: {DEFAULT_SHARD_ROOT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be copied without writing",
    )
    args = parser.parse_args()

    # Clean destination before syncing (unless dry run)
    if not args.dry_run and FIXTURE_DIR.exists():
        print(f"Cleaning {FIXTURE_DIR}...")
        shutil.rmtree(FIXTURE_DIR)

    sync_fixtures(args.shard_root, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
