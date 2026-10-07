---
name: war3-save-reverse
description: Reverse engineer, decode, repair, migrate, and patch Warcraft III save and campaign data, including .w3z saved games, .w3v game caches/Campaigns.w3v, .w3n custom campaigns, .w3x maps, MPQ extraction/update, war3map.j JASS inventory/equipment migration, custom campaign item/object data in .w3t/.wts, missing load-screen saves, load errors, and campaign chapters that lose hero equipment.
---

# Warcraft III Save Reverse

Use this skill for Warcraft III save/cache/campaign reverse engineering where correctness depends on binary structure, MPQ archives, game-cache state, or JASS map scripts.

## Operating Rules

- Back up the exact live file before every write. Use timestamped `.bak-YYYYMMDD-HHMMSS-<reason>` names.
- In `%USERPROFILE%\Documents\Warcraft III`, keep live Warcraft III data in place but store generated tooling and large work artifacts outside that live-data tree.
- Use `%WAR3_CODEX_ROOT%` as the work root when configured; otherwise default to `%LOCALAPPDATA%\War3CodexTools\WarcraftIII`:
  - Reusable root helpers: `<work-root>\tools`
  - Migrated scan/temp/tool workdirs: `<work-root>\workdirs`
  - Scratch campaign/save copies: `<work-root>\scratch-campaigns`
  - Active per-task workdirs: `<work-root>\tasks\<task-name>`
  - Large backups: `<work-root>\backups`
- When using migrated Python helpers, add `<work-root>\tools` and, when needed, `<work-root>\workdirs\_war3_tmp` to `sys.path`. Avoid creating large `_war3_tmp`, `.tmp_*`, extracted MPQ, or scratch `.w3n/.w3x/.w3z/.w3v` files under the Documents live-data root.
- Do not reuse a worse source save when the user identifies a better source. Preserve the user's chosen source name in notes and commands.
- Verify by extracting the live artifact back out and comparing hashes or content. Do not trust a write tool's "OK" alone.
- Prefer one reversible change per test. If the game reports "load error", roll back or patch only the smallest suspected fault.
- Treat old in-game saves as stale after campaign/map script changes. Test from the campaign/chapter entry point unless the user explicitly asks to repair a saved-game slot.

## Workflow

1. Identify the target layer.
   - Save visibility/load failure: inspect `.w3z` or `.w3v` outer save container first. See `references/w3z-w3v-format.md`.
   - Missing campaign equipment after entering a chapter: inspect game cache and the target map's `war3map.j`. See `references/war3-gamecache-equipment.md`.
   - Custom campaign or map edits: patch `.w3n`/`.w3x` MPQ contents and verify by re-extraction. See `references/mpq-jass-patching.md`.
   - Custom item/object definitions: patch `war3campaign.w3t`/`war3campaign.wts` or map-level `war3map.w3t`/`war3map.wts` with structured object-data tooling. See `references/war3-custom-items.md`.
   - Hero skill, model, skin, sound, scale, or ability-set migration: inspect both campaign-level and map-level unit/ability/buff/string data before patching scripts. See `references/war3-skill-model-migration.md`.

2. Locate the live path.
   - Check `Documents\Warcraft III\Campaigns`, `Documents\Warcraft III\BattleNet\<region>\<account>\<profile>`, and any known install/profile path the user mentions.
   - If several copies exist, compare timestamps and ask the user to test only when path identity cannot be determined from files.

3. Decode or patch with deterministic tooling.
   - Use `scripts/w3z_tool.py` for `.w3z`/`.w3v` unpack, pack, inspect, and rawcode scan.
   - Use `scripts/sfmpq_extract.c` and `scripts/sfmpq_update.c` as rebuildable SFMPQ helpers when no external MPQ tool is available.
   - For `.w3t` object data, use a parser/editor that roundtrips the original file byte-identical before editing. Do not patch binary `.w3t` files with ad hoc text replacement.
   - For equipment mismatches, do not trust a single cache or narrow address-range scan. Decode the source save and scan the full raw file for runtime owner-held item records, then use campaign object/string data to resolve custom item names. Treat any campaign-specific save name, hero handle, rawcode, and marker as data to rediscover, not reusable defaults.

4. Verify before reporting.
   - For save containers: unpack the rebuilt file and compare raw bytes or expected byte ranges.
   - For MPQ patches: extract the target file from the live archive, hash it against the patched source, and grep for expected markers.
   - For JASS patches: check function order, local declarations, duplicate function names, and rawcode literals before asking the user to test.
   - For custom item data: re-extract the live `.w3t`/`.wts`, parse the object record, verify ability/string fields, and compare hashes against the patched source.

## Common Commands

Inspect a save/cache container:

```powershell
python "$env:USERPROFILE\.codex\skills\war3-save-reverse\scripts\w3z_tool.py" inspect path\to\save.w3z
```

Unpack and repack using the original file as the header template:

```powershell
python "$env:USERPROFILE\.codex\skills\war3-save-reverse\scripts\w3z_tool.py" unpack source.w3z source.raw.bin
python "$env:USERPROFILE\.codex\skills\war3-save-reverse\scripts\w3z_tool.py" pack source.w3z edited.raw.bin output.w3z
python "$env:USERPROFILE\.codex\skills\war3-save-reverse\scripts\w3z_tool.py" unpack output.w3z verify.raw.bin
```

Scan a raw decoded save/cache for Warcraft object rawcodes:

```powershell
python "$env:USERPROFILE\.codex\skills\war3-save-reverse\scripts\w3z_tool.py" scan-rawcodes source.raw.bin bonc ziwr J06I
```

## Reference Selection

- Read `references/w3z-w3v-format.md` when repairing invisible/unloadable saves or modifying `.w3z`/`.w3v`.
- Read `references/war3-gamecache-equipment.md` when moving hero inventory/equipment between saves, chapters, or game caches.
- Read `references/mpq-jass-patching.md` when editing `.w3n`/`.w3x`, `war3map.j`, campaign chapter scripts, or fixing "load error" after a patch.
- Read `references/war3-custom-items.md` when adding or overriding custom items, copying an item definition from another map/campaign, or when a rawcode's behavior depends on `.w3t`/`.wts` object data.
- Read `references/war3-skill-model-migration.md` when changing hero skills, aura behavior, spell-damage modifiers, unit models, skins, scale, sound sets, cloned custom abilities, or when a restored campaign hero ignores an object-data model change.
