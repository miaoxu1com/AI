# Warcraft III Skill and Model Migration

Use this reference when a custom campaign needs hero skills, unit models, skins, scale, sound sets, or related custom ability data migrated from another campaign/map. It is also the checklist for future "make this hero use that model/skill set" work.

Do not treat any rawcode, map name, hero variable, or campaign-specific helper from the examples as reusable. Rediscover them in the current campaign.

## Scope

Skill/model changes can require all of these layers:

- Campaign-level unit, ability, buff/effect, and string data: `war3campaign.w3u`, `war3campaign.w3a`, `war3campaign.w3h`, `war3campaign.wts`.
- Map-level unit, ability, buff/effect, and string data: `war3map.w3u`, `war3map.w3a`, `war3map.w3h`, `war3map.wts`.
- Imported assets: MDX/MDL models, BLP icons/textures, DISBTN icons, portrait models, missile/effect models.
- Chapter script: inner `scripts\war3map.j` or `war3map.j`.
- Campaign game-cache boundaries: `StoreUnit`, `RestoreUnit`, `SaveGameCache`, `ReloadGameCachesFromDisk`, and chapter entry/exit triggers.

Campaign-level data alone is not proof that a chapter will use the change. A map-level object record can override it, and some chapters require map-level records even when campaign-level data exists.

## Required Workflow

1. Back up the exact live `.w3n` or `.w3x` before writing.
2. Extract the campaign archive and every target chapter map.
3. Inspect campaign-level object data.
   - Units: resolve target unit rawcodes and fields such as model, scale, sound set, hero ability list, normal ability list, attack art, icon, and requirements.
   - Abilities: resolve every custom ability id used by the desired skill set.
   - Buffs/effects: resolve every buff, aura target art, effect model, missile model, and icon dependency referenced by the abilities.
   - Strings: resolve every `TRIGSTR_*` used by name, tooltip, ubertip, learn tooltip, and hotkey fields.
4. Inspect each target map's map-level object data.
   - If `war3map.w3u` contains the target unit rawcode, patch that map-level record too.
   - If `war3map.w3a` or `war3map.w3h` contains colliding ability/buff ids, decide whether to replace, remap, or allocate fresh ids.
   - If a chapter lacks the custom data that restored heroes/items/abilities need, import it into that chapter map before patching JASS.
5. Clone source abilities structurally.
   - Copy the source ability records, all referenced buffs/effects, and all string records.
   - Copy icons, DISBTN icons, models, portraits, textures, and effect assets referenced by those records.
   - Preserve object-data version when a target chapter is sensitive to version conversion; if a v3 conversion causes load hangs, restore and retry with source-compatible map-level object-data serialization.
6. Patch unit records only after dependencies exist.
   - Set the model/portrait/icon/sound/scale fields in every level that can affect the target chapter.
   - Set hero skills as a complete ordered list, not an additive append, unless the user explicitly wants both old and new skills.
   - Verify no copied skill is missing its dependency chain.
7. Patch JASS only after object data exists.
   - Insert helper functions immediately after `endglobals` unless the map already has a safer local helper section.
   - Call helpers after the hero is created or restored, never before the target unit variable is assigned.
   - Keep local declarations at the top of functions and avoid duplicate helper names.
8. Make the change persistent across chapter boundaries.
   - Search all relevant maps for the target rawcodes, hero variable names, `StoreUnit`, `RestoreUnit`, `InitGameCacheBJ`, and chapter cache names.
   - Patch every playable chapter that can restore the hero or store the changed hero for the next chapter.
   - If one chapter entry uses map-level object data, assume the next restored chapter may need the same object data until verified otherwise.
9. Verify from the live archive.
   - Re-extract the edited live `.w3n`.
   - Re-extract every patched `.w3x`.
   - Hash-compare edited files against the patched sources.
   - Parse the live object files and verify the final unit, ability, buff/effect, and string records.
   - Grep live scripts for marker/helper names and expected rawcodes.
   - Perform an all-map read smoke test when campaign-level object data changed.
10. Test from the campaign/chapter entry point. Old in-game saves are stale after object-data or script changes.

## Runtime Replacement for Restored Heroes

Restored campaign heroes can keep old runtime state even after object data changes. In that case a simple `BlzSetUnitSkin` or object-data patch may not visibly update the model.

Use the least invasive runtime method that works:

1. Try object-data patching at the correct campaign/map level.
2. If restored state still shows the old model, try `BlzSetUnitSkin` after restore.
3. If skin-only does not work, use a controlled rebuild:
   - Save owner, location, facing, level, life/mana percentages, inventory, and any campaign-critical state.
   - Create the replacement with `BlzCreateUnitWithSkin`.
   - Reapply level, skills, inventory, selection/camera handling, and cache variable assignment.
   - Remove or hide the old unit only after the replacement is assigned.
   - Avoid creating duplicate heroes on repeated trigger execution.

Keep replacement helpers campaign-specific, named with a unique marker, and placed before callers. Do not use a case-study helper name or rawcode in another campaign without rediscovery.

## Skill Points

Do not add hero skill points blindly. Ability-list changes can expose unspent points from prior leveling or from the map's own initialization.

- Measure the in-game expected point count and the script's existing level/skill-point calls.
- Prefer `ModifyHeroSkillPoints(u, bj_MODIFYMETHOD_SET, exactCount)` when the user wants an exact starting state.
- Use `ADD` only when the existing points are known and the additive behavior is desired.
- Verify by chapter entry. A stale saved game can show the old skill state or extra points.

## Load-Failure Recovery

If the map or campaign becomes unloadable after a skill/model migration:

1. Restore the newest exact `before-...` backup.
2. Reapply only one layer at a time: object data first, then assets, then JASS.
3. Keep campaign-level object files unchanged if a broad import makes unrelated chapters hang; retry as map-level imports for only the target chapter.
4. Check object-data version compatibility, missing dependency ids, duplicated object ids, MPQ file-count limits, and duplicate MPQ entries.
5. Verify by re-extracting and parsing the live archive before asking the user to test again.

Do not stack fixes on a broken archive.

## Case Study: Alliance Bolvar Holy Aura Spell Damage Amp

This is a reproducibility note for Reforged-era spell-damage aura edits, not a reusable patch script.

Confirmed target in `联盟史诗-暴风崛起v1.1.1 单机版`:

```text
Campaign aura rawcode: A610
Aura buff rawcode: B606
Playable chapter maps: Bolvar00.w3x through Bolvar12x.w3x
Final behavior: non-attack damage from a source carrying B606 is set to 130% of the original event damage.
```

Important failures and fixes:

- The file name said `1.27+`, but the successful implementation targeted Reforged. Do not force a 1.27-compatible damage system when the user confirms Reforged.
- Object data alone could only make the aura apply a buff; it could not natively give allied casters a 30% spell-damage output bonus. The campaign-level `war3campaign.w3a` needed `A610.abuf = B606` for all levels, and the chapter scripts needed damage-event logic.
- Failed attempts used target-side vulnerability or an extra `UnitDamageTarget(..., dmg * 0.30, ...)` bonus hit. The target-side version changed the semantics, and the bonus-hit version created a second damage event with different damage-type/resistance behavior and possible recursion.
- The durable Reforged path was: register `EVENT_PLAYER_UNIT_DAMAGING`, read `GetEventDamageSource()`, skip attacks with `BlzGetEventIsAttack()`, require `GetUnitAbilityLevel(src, 'B606') > 0`, require `IsUnitEnemy(GetTriggerUnit(), GetOwningPlayer(src))`, then call `BlzSetEventDamage(dmg * 1.30)`.
- This modifies the same damage instance, so it does not need a recursion guard for the percentage bonus itself. If the script also creates new damage elsewhere, audit those paths separately.
- Campaign-level `A610` had no map-level `war3map.w3a` overrides for the Bolvar maps, so the object-data tooltip/buff edit belonged at campaign level while the JASS patch had to be applied to every relevant chapter map.
- Verification must re-extract the live `.w3n` and every patched `Bolvar*.w3x`, then confirm each script has exactly one `EVENT_PLAYER_UNIT_DAMAGING`, one `BlzSetEventDamage(dmg * 1.30)`, one `GetUnitAbilityLevel(src, 'B606')`, no old `OMX_DE_Modify`, no `UnitDamageTarget(OMX_DE_Source...)`, and no debug markers such as `StartSound(gg_snd_QuestNew)`.
- Verify `A610` after re-extraction: every level should use `B606`, the aura range/regen fields should remain intact, and tooltips should describe "allied units inside the aura deal 30% more spell/skill damage" rather than "enemies in range take more spell damage".
- Test from a chapter entry point. Old saved games can preserve stale script/object state and should not be the first validation surface.

## Case Study: Guanhequ Jurchen Wizard Fire-Rain Skin Over High-Frequency Blizzard

This is a reproducibility note for making a Reforged custom campaign spell look and read like Fire Rain while preserving the proven high-frequency Blizzard damage logic.

Confirmed target in `关河曲v1.41【1.31+】`:

```text
Target unit rawcode: unec
Target ability rawcode: A6RF
Working base ability: ACbz
Custom status buff rawcode: B6RF
Fire rain special effect: XErf
Verified command/status icon: war3campImported\BTNTwilightFire.blp
Verified target burn art: war3campImported\twilightincineratebuff.mdx
Reference source behavior: 猩红狂热2 high-frequency Blizzard, copied structurally rather than approximated
Final burn overlay: 20 fire magic damage per second
```

Important failures and fixes:

- Do not switch the working ability back to a native Rain of Fire base such as `ACrg` just to get the theme. In this campaign, `ACrg`-based attempts produced good visuals but no reliable damage or the wrong hit cadence.
- The durable path was to preserve a Blizzard-derived ability (`old_id ACbz`) and copy the source campaign's high-frequency Blizzard object fields into the target ability. For the verified `A6RF`, keep the dense Blizzard fields such as `Hbz1/Hbz3 = 48`, `Hbz2/Hbz5 = 12`, `adur/ahdu = 2.5`, and `acas = 0.1`.
- Treat visuals, text, and logic as separate layers. Change only safe presentation fields on the working ability: `anam`, `atp1`, `aub1`, `aart`, `aeff = XErf`, and the tooltip strings. Do not rewrite the native damage engine once the Blizzard cadence is confirmed in game.
- Do not assume the standard-looking `ReplaceableTextures\CommandButtons\BTNRainOfFire.blp` path exists in the user's current Reforged/resource setup. In this campaign it produced missing command-card and status-bar icons. The verified fix was to use the campaign-imported fire-rain-family icon already used by existing `ANrf/ACrg` rain spells: `war3campImported\BTNTwilightFire.blp`, with the existing disabled icon `ReplaceableTextures\CommandButtonsDisabled\disbtntwilightfire.blp`.
- If the status bar still displays Blizzard text/icon, clone a Blizzard buff rather than reusing the default one. The verified fix was `B6RF` based on `BHbz`, with Fire Rain name, `fart = war3campImported\BTNTwilightFire.blp`, and buff text describing the per-second burn; then set `A6RF.abuf = B6RF`.
- If burned units have no body effect, inspect existing campaign Rain of Fire damage buffs rather than guessing a native path. In this campaign, the existing dark rain damage buff `B61S` (`old_id BNrd`) supplied the target burn model: `ftat = war3campImported\twilightincineratebuff.mdx`. Because `B6RF` deliberately remained `old_id BHbz`, copy the visual fields explicitly onto `B6RF`: `ftat = war3campImported\twilightincineratebuff.mdx` and `fta0 = chest`.
- Add scorch/burn damage as a separate JASS overlay when native object data cannot express the desired residual burn without breaking the confirmed hit pattern. Gate the trigger on `GetSpellAbilityId() == 'A6RF'`, enumerate units in the target area for the desired duration, and apply a fixed periodic `UnitDamageTarget(caster, u, 20.00, true, false, ATTACK_TYPE_MAGIC, DAMAGE_TYPE_FIRE, null)` or campaign-equivalent call. Keep helper names unique and verify there is exactly one gate and one damage literal per patched map.
- When copying from a source campaign where the desired Rain of Fire burn is native, inspect the source ability before assuming object fields exist. In the successful Guanhequ patch, the strongest source Rain of Fire behavior did not expose a useful custom burn field to copy directly, so the reliable burn was implemented by trigger overlay.
- Patch all campaign maps that can expose the unit or ability, not only the currently tested chapter. For this campaign, the successful patch covered the maps named from the campaign `(listfile)` that contained `unec`, `A6RF`, or the relevant Jurchen wizard data, including playable and interlude maps.
- Verification must re-extract the live `.w3n`, then parse live `war3campaign.w3a`, `war3campaign.w3h`, `war3campaign.wts`, and every patched map script. Confirm `A6RF` remains `old_id ACbz`, `A6RF.aart` and `B6RF.fart` use `war3campImported\BTNTwilightFire.blp`, `B6RF.ftat = war3campImported\twilightincineratebuff.mdx`, `B6RF.fta0 = chest`, `A6RF.abuf = B6RF`, `A6RF.aeff = XErf`, tooltips mention Fire Rain and the correct burn value, every patched script has `20.00` burn damage, no old `10.00` burn literal remains, and map-level `war3map.w3a/war3map.w3h` does not override `A6RF/B6RF`.
- Preserve unrelated successful edits while iterating. Earlier Guanhequ work had chapter-specific witch Holy Ray and gryphon skill edits; Fire Rain retries should restore only the failed Fire Rain layer, not roll back unrelated chapter/unit changes.

## Case Study: Silver Ash Darion Model and Skill Migration

This is a reproducibility example, not a reusable patch script.

Confirmed target in `灰烬使者-银色之史（1.36+）`:

```text
Campaign unit rawcodes: H609, H60A
Desired model: units\human\Arthas\Arthas.mdl
Sound set: Arthas
Combat sound: MetalHeavyBash
Final hero skills: AHhb, AHtc, A90C, A90J
Final scale: usca = 0.90
LoA06 entry skill points: SET 5
```

Important failures and fixes:

- Editing only `war3campaign.w3u` did not affect every chapter. LoA06 needed map-level `war3map.w3u` records for `H609/H60A`.
- `BlzSetUnitSkin` alone did not reliably update the restored hero. LoA06 needed a runtime rebuild with `BlzCreateUnitWithSkin(p, 'H609', x, y, f, 'H609')` after restore.
- Later restored chapters can regress even after an earlier rebuild. LoA07/LoA07b restored Darion from `LoA6` and still needed the rebuild helper, not skin-only. When rebuilding a persistent hero outside a fresh chapter-entry gear grant, preserve hero level, XP, unspent skill points, learned skill levels, life/mana, and six inventory slots before removing the old unit.
- Additive skill-point patches were wrong. `ADD 8` produced 14 points, `SET 8` still left 2 extra points, and `SET 6` still left 1 extra point for that chapter state. The verified target was `SET 5`.
- Patching only one chapter risked reversion after game-cache restore/store. The persistent fix had to account for LoA04-LoA09 chapter boundaries.
- Verification required re-extracting the live campaign and target maps, parsing live object data, checking JASS helpers, and testing from chapter entry rather than an old save.
- Monsoon-based Ash Judgment migration exposed a field-placement and source-logic trap. The source ability used native object data, not JASS: `A60B/A60G old ANmo`, `B600 old ANmd`, and `X600 old XNmo`; `B600.ftat = war3campImported\JudgementTarget.mdx`, while `X600.feat = Abilities\Spells\Other\Andt\Andt.mdl` and had no `X600.ftat`. Compare source and target records field-by-field and search source maps for `GetSpellAbilityId`, `UnitDamageTarget`, and the source rawcodes before patching. In this source campaign, root and map `(listfile)` entries showed only `war3campImported\JudgementTarget.mdx` and no override for default Monsoon bolt assets; source map scripts did not implement Ash Judgment damage. Therefore the source-faithful migration is native `ANmo` object data (`abuf`, `aeff`, `Esf1`, `adur/ahdu`, `atar`) plus required target flags such as `structure`, not a JASS reimplementation. Do not add all-range or native-like simulated damage triggers by default.
- Reforged has a known Starfall/Monsoon visual quirk: cloned `ANmo` abilities may honor the copied buff/effect for cast/start art but keep using the original Monsoon periodic hit visual. When the user wants the periodic hit visual fixed and accepts the global side effect, apply the object-data workaround instead of scripting a fake Monsoon: override the original effect records `ANmd.ftat = war3campImported\JudgementTarget.mdx` and `XNmo.feat = Abilities\Spells\Other\Andt\Andt.mdl` at campaign level, then also patch any target chapter map-level `war3map.w3h` that exists. Keep the cloned `B90J/X90J` records with the same fields because older engines or non-bugged contexts may still read them. Verify by re-extracting `war3campaign.w3h` and each patched map `war3map.w3h`, checking both the original records (`old_id ANmd/XNmo` with zero `new_id`) and the cloned records (`B90J/X90J`). Document the tradeoff: every Starfall/Monsoon-derived ability in those object-data scopes can inherit the changed original periodic visual.
- The attempted LoA07/LoA07b Darion Arthas-model persistence path was later rolled back because LoA08 could still receive a no-model Darion through campaign cache. Do not reuse that attempt as a success pattern. The rollback kept non-model gameplay edits but removed model forcing by making `OMX_ForceSilverDarionArthasModel` return the input unit unchanged in LoA04-LoA09, making `OMX_RebuildSilverDarionArthasHero` return the old unit in LoA06, and deleting `umdl/usca/usnd/ucs1` overrides from `H609/H60A` in campaign-level and map-level `w3u` data. When reverting model experiments, preserve unrelated skill/equipment/effect edits and verify no helper still calls `BlzSetUnitSkin`, `BlzCreateUnitWithSkin`, `CreateUnit`, `SetUnitScalePercent`, `RemoveUnit(old)`, or `ModifyHeroSkillPoints(nu, ...)` for Darion model forcing.
- Unit availability can be blocked by chapter script even when object data looks correct. LoA07b workers already inherited a build list with `hgra`, but `InitTechTree_Player0` set `hgra` max allowed to `0`; the durable fix was to patch the chapter script and map-level `war3map.w3u` together. For trained units that need level-3 base/hero abilities, add the abilities in map-level unit data and also register train/enter-map triggers that call `SetUnitAbilityLevel(..., 3)`.

Use this example to remember the method: inspect both object-data levels, patch dependencies before script, handle restored heroes explicitly, set exact skill points, and verify across cache boundaries.
