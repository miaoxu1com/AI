# Warcraft III Custom Item/Object Data

Use this reference when a campaign or map needs a custom item definition, or when a base rawcode only has the desired behavior in another map because that map overrides object data.

## Scope

Warcraft item behavior can come from:

- Base game SLK data such as `War3Patch/Units/ItemData.slk`.
- Campaign-level custom data: `war3campaign.w3t` plus `war3campaign.wts`.
- Map-level custom data: `war3map.w3t` plus `war3map.wts`.

If a script grants an item rawcode, the target campaign/map must also contain the object data that makes that rawcode behave as intended.

## Rules

- Back up the live `.w3n` or `.w3x` before every write.
- Prefer campaign-level `war3campaign.w3t`/`war3campaign.wts` for items that should be usable across campaign chapters. If the imported item set is only needed in one chapter, especially from a campaign with older object-data versions, prefer map-level `war3map.*` first to limit blast radius.
- Inspect map-level `war3map.w3t` first; a map-level record can override campaign-level assumptions.
- Treat `.w3t` as binary object data. Use a structured parser/editor and prove it can roundtrip the original file byte-for-byte before editing.
- Preserve raw 4-byte ids, value types, and object-modification end ids unless intentionally changing them.
- Do not assume a display name implies a rawcode. Resolve the rawcode through `.wts` string references and `.w3t` object records.

## Workflow

1. Extract the live target files.
   - Campaign object data: `war3campaign.w3t`, `war3campaign.wts`.
   - Target chapter map if a script also changes: `ChapterNN.w3x`, then inner `scripts\war3map.j`.

2. Extract the source object data if copying from another map/campaign.
   - Copy source maps to a local temp path first when Windows MPQ helpers cannot open paths with spaces directly.
   - Extract source `war3map.w3t`/`war3map.wts` or `war3campaign.w3t`/`war3campaign.wts`.

3. Resolve the source object.
   - Search the source `.wts` for the displayed item name.
   - Search the source `.w3t` for the matching `TRIGSTR_<id>`.
   - Confirm the object rawcode and important fields such as `iabi` (ability list), `icid` (cooldown id), `unam`, `utip`, `utub`, and `ides`.
   - Compare against base `ItemData.slk` to catch misleading rawcodes.

4. Roundtrip before editing.
   - Parse the original target `.w3t`.
   - Re-serialize it without changes.
   - Compare bytes with `cmp` or hashes. If it is not byte-identical, fix the parser before patching.

5. Add or replace the target object record.
   - If overriding a base item rawcode, keep the source shape: usually `old_id=<base rawcode>` and `new_id=0000`.
   - If creating a new custom item from a base item, use `old_id=<base rawcode>` and `new_id=<new custom rawcode>`.
   - Remove any existing target record for the same rawcode before inserting a replacement.
   - Preserve the source record's table placement unless there is a known reason to move it.

6. Add target strings.
   - Pick unused `STRING` ids higher than the target `.wts` max id.
   - Append name, tooltip, ubertip, and description strings.
   - Update the object fields to the new `TRIGSTR_<id>` values.

7. Patch scripts only after object data is ready.
   - If the chapter grants the item, patch the innermost `scripts\war3map.j` in the chapter `.w3x`.
   - Then replace the chapter `.w3x` inside the campaign `.w3n`.

8. Write and verify.
   - Back up the exact live archive.
   - Write `war3campaign.w3t`/`war3campaign.wts` and any patched chapter `.w3x`.
   - Re-extract the live archive.
   - Hash-compare re-extracted files against patched sources.
   - Parse the live `.w3t` and verify the object fields.
   - Grep the live `.wts` for the new strings.
   - If a map script changed, re-extract the live map and compare its inner script hash.

## Example: Orgrimmar Battle Standard

Do not use `oflg` for the Orgrimmar Battle Standard. In base 1.27a data, `oflg` is `Orc flag` with `AIfo`.

The Durotar campaign's Orgrimmar Battle Standard uses rawcode `btst`. Base `btst` is only `orcish battle standard` with `AIfx`, but Durotar map object data overrides `btst` to include:

```text
iabi = AIfx,AIx5,AIav
icid = AUav
```

For an Arkain-style campaign-level import:

1. Copy the Durotar `btst` object record from source `war3map.w3t`.
2. Add or replace `btst` in target `war3campaign.w3t`.
3. Add target `war3campaign.wts` strings and update `ides`, `unam`, `utip`, `utub`.
4. Verify the live campaign parses with `btst` containing `AIfx,AIx5,AIav`.
5. Only then grant `'btst'` in chapter JASS.

`AIav` is the Vampiric Aura item ability. It is different from `AIva` lifesteal attack modifiers such as Mask of Death, which can conflict with orb effects.

## Regression Example: COTF Ch08 Scarlet Final Gear

This example documents a confirmed failure and recovery when migrating the final two-hero gear from `猩红狂热II v2.41.w3n` chapter `ScarletCrusader10.w3x` into `被遗忘者的诅咒` chapter `Forsaken08.w3x`.

Source gear discovered from the source quicksave/cache:

```text
Abbendis -> H602/Varian: srbd, I62I, I62H, ram3, I62N, I62Y
Jordan   -> H60R/Bolvar: I62R, ram1, olig, I63K, I62S, I61X
```

Failure path:

1. Importing the 12 items plus cloned ability/buff dependencies into campaign-level `war3campaign.w3t/.w3a/.w3h/.wts` made unrelated chapters hang during loading. File-level extraction and parser checks still passed, so successful MPQ writes were not enough proof.
2. Moving the same object set into `Forsaken08.w3x` map-level files fixed the unrelated chapters but chapter 8 still hung when the imported object data was serialized as the target map's v3 object format.

Successful path:

1. Restore the exact pre-patch `.w3n` backup before retrying. Do not stack fixes on the broken archive.
2. Patch only `Forsaken08.w3x` inside the campaign; leave `war3campaign.w3t/.w3a/.w3h/.wts` byte-identical to the known-good campaign.
3. Put the imported items in map-level `war3map.w3t`, clone item abilities into map-level `war3map.w3a`, and clone buffs into map-level `war3map.w3h`.
4. Preserve object type prefixes when allocating fresh ids: abilities used `A800..A80O`, buffs used `B800/B801`. Do not allocate ability ids under non-ability prefixes such as `Z...` or buff ids under `Y...`.
5. Serialize the patched map-level object files as object-data version 2 to match the older source campaign shape. The target map originally had v3 map object files, but the v3-converted import hung during chapter loading.
6. Append source `TRIGSTR_*` text to map-level `war3map.wts` and rewrite the copied records to the new map string ids.
7. Copy all referenced custom icons/models into the same `Forsaken08.w3x`; re-extract and hash-compare each resource. Missing icons usually produce green icons, not global chapter load hangs, but model/icon dependencies still need verification.
8. Re-extract the live `.w3n`, confirm only `Forsaken08.w3x` changed at the campaign layer, then re-extract the inner map and parse/hash `war3map.j`, `war3map.w3t`, `war3map.w3a`, `war3map.w3h`, `war3map.wts`, and resources.

Use this case as the default recovery pattern when a one-chapter equipment import makes a chapter hang at load: first restore, then retry with map-level object data and the source-compatible object-data version before broader campaign-level imports.

### Persistence Follow-up: COTF Ch09 Scarlet Final Gear

If the chapter 8 gear appears correctly but disappears after moving into `Forsaken09.w3x`, do not treat it as a failed chapter 8 save by default. In the confirmed COTF case, chapter 8 stored `Varian` and `Bolvar` into `Forsaken08.w3v`, and chapter 9 restored those units, but chapter 9 did not have the imported Scarlet item definitions. The fix was to patch `Forsaken09.w3x` itself with the same map-level v2 `war3map.w3t/.w3a/.w3h/.wts` object set and to call a small JASS re-equip helper immediately after:

```jass
call ConditionalTriggerExecute(gg_trg_RestoreBolvar)
call ConditionalTriggerExecute(gg_trg_RestoreVarian)
```

Keep this follow-up map-level as well. Do not reintroduce the Scarlet objects into campaign-level `war3campaign.w3t/.w3a/.w3h/.wts`, because that was the path that made unrelated chapters hang.

`Forsaken09.w3x` also exposed a separate MPQ capacity trap: its archive `MaxFileCount` was only 64. The SFMPQ update helper could replace existing core files and add the 24 icon BLPs, then failed on the first MDX model because the archive had no room for more new file entries. Use StormLib/StormLibSharp or another MPQ tool that can increase max file count, set it high enough (4096 was used successfully), remove existing `war3map.*` entries before adding replacements, then add the new map object files and resources. If existing files are not removed first, some tools add duplicate entries and extraction can still return the old `war3map.j`.

Verification for this persistence fix must include:

1. Re-extract `Forsaken09.w3x` from the live `.w3n` and hash-compare it to the patched map.
2. Re-extract inner `war3map.j/.w3t/.w3a/.w3h/.wts` plus all imported icons/models from the live `Forsaken09.w3x`.
3. Parse the live map object data and verify the 12 Scarlet items, cloned `A...` abilities, and cloned `B...` buffs.
4. Confirm `Forsaken08.w3x` and campaign-level object files remain byte-identical to the pre-follow-up live campaign.
