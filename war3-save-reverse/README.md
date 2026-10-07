# Warcraft III Save Reverse

A Codex skill for safely inspecting, repairing, migrating, and patching Warcraft III save files, game caches, custom campaigns, maps, JASS scripts, and custom object data.

## Capabilities

- Inspect, unpack, repack, and verify `.w3z` saved games and `.w3v` game caches.
- Patch `.w3n` custom campaigns and `.w3x` maps through deterministic MPQ workflows.
- Diagnose campaign chapters that lose hero inventory or equipment.
- Migrate hero skills, models, skins, sounds, scale, abilities, and custom object data.
- Validate changes by re-extraction, hashing, byte comparison, and script checks.

## Install

PowerShell:

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
git clone https://github.com/dc114154qq/war3-save-reverse.git (Join-Path $codexHome "skills\war3-save-reverse")
```

Restart Codex after installation, then invoke the skill with `$war3-save-reverse` or describe a Warcraft III save/campaign repair task that matches its scope.

## Repository layout

- `SKILL.md` — workflow, safety rules, routing, and validation requirements.
- `references/` — format notes and task-specific repair guidance.
- `scripts/w3z_tool.py` — `.w3z`/`.w3v` inspection, unpacking, packing, and rawcode scanning.
- `scripts/sfmpq_extract.c` and `scripts/sfmpq_update.c` — small Windows SFMPQ helper sources.
- `agents/openai.yaml` — Codex skill metadata.

## Requirements

- Codex with local skill support.
- Python 3.8 or newer for `w3z_tool.py`.
- Windows and an available `sfmpq.dll` for the optional C MPQ helpers. Set `SFMPQ_DLL` when the DLL is not on `PATH` or in the standard Warcraft III installation path.

## Safety

The skill is intentionally conservative: it requires timestamped backups before writes, one reversible change per test, and verification against the rebuilt live artifact. Do not commit real save files, game caches, campaign archives, account identifiers, or extracted proprietary game assets to this repository.
