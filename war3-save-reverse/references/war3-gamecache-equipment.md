# Game Cache and Equipment Migration

## Scope

Use this reference when campaign hero equipment is lost between chapters, when `Campaigns.w3v` or `Maiev03.w3v` needs repair, or when a target chapter must inherit inventory from a known source save.

## Important Distinction

Warcraft campaign state can live in more than one place:

- `.w3z` saved game: a full in-map runtime state.
- `Campaigns.w3v`: campaign-level progress/state.
- `<chapter>.w3v` or named game cache: cross-map hero cache used by campaign scripts.
- `war3map.j` inside a chapter map: script that decides which cache sections are restored and when items are created.

Changing only one layer can be insufficient. If the target chapter script ignores the cache, restores different keys, or overwrites inventory later, the in-game result remains empty.

## Game Cache Restore Pattern

In JASS, campaign chapters commonly use:

```jass
call ReloadGameCachesFromDisk()
call InitGameCacheBJ("Maiev03.w3v")
call RestoreUnitLocFacingAngleBJ("Maiev03", "Chapter03", udg_MaievAkamaCache, ...)
call RestoreUnitLocFacingAngleBJ("Anyndra03", "Chapter03", udg_MaievAkamaCache, ...)
```

To diagnose empty equipment:

1. Extract the target `war3map.j` from the `.w3x`.
2. Search for `ReloadGameCachesFromDisk`, `InitGameCacheBJ`, `RestoreUnit`, hero variable names, and inventory-clearing functions.
3. Confirm exact cache file and section/key strings.
4. Confirm whether later triggers replace the hero or clear inventory after restore.

## Rawcodes and JASS FourCC Endianness

In decoded raw save/cache data, item IDs often appear as readable four-byte ASCII strings, for example:

```text
bonc
ziwr
J06I
```

In JASS integer literals, Warcraft stores FourCC values as big-endian-looking character constants. For this workspace's successful patch, the raw bytes had to be reversed when written as JASS literals:

```text
raw bytes  JASS literal
bonc       'cnob'
J06I       'I60J'
nehs       'shen'
1gar       'rag1'
ziwr       'rwiz'
dpsb       'bspd'
G06I       'I60G'
I06I       'I60I'
1nir       'rin1'
1edr       'rde1'
1tsr       'rst1'
namp       'pman'
```

Do not assume this blindly for every edit. Verify by testing with one known item or by comparing an existing map's JASS literals to decoded raw bytes.

## General Inventory Extraction Workflow

Use this workflow for any campaign/save pair. Do not copy rawcodes, handles, cache names, or markers from another campaign unless independently verified in the current files.

1. Identify the source save the user wants to inherit from and unpack it to raw bytes.
2. Identify the target campaign and chapter map, then extract the target `war3map.j`.
3. Find the relevant source heroes by hero name, unit rawcode, cache key, or runtime unit record.
4. Locate each hero's runtime owner handle from the full decoded save, not only from one address range.
5. Scan the full decoded save for item records whose owner pair matches the hero handle.
6. Cross-check against game-cache sections only as supporting evidence. If cache inventory and runtime inventory disagree, prefer runtime-held items when the user is asking for the current save state.
7. Resolve custom item names through object/string files before patching.
8. Patch the target chapter script after hero creation/restore, clear inventory, grant the verified source items, and add a campaign-specific visible marker.
9. Verify by extracting the live campaign back out and comparing the patched script hash and marker.
10. Ask the user to test from the chapter entry point, not from a stale in-map save.

If the source items require custom object data and the target chapter hangs during loading after import, switch to the recovery pattern in `war3-custom-items.md` under "COTF Ch08 Scarlet Final Gear": restore the pre-patch archive, keep campaign-level object files unchanged, import the object data into the target map only, and preserve the source-compatible object-data version.

If equipment appears in one patched chapter but disappears in the next chapter after a game-cache restore, inspect the next chapter as a separate target map. The cache may restore the units correctly while custom items are dropped or downgraded because the next map lacks the same map-level object definitions. In the confirmed COTF Scarlet gear follow-up, `Forsaken09.w3x` needed its own map-level v2 object-data import and a post-restore re-equip call; see `war3-custom-items.md` under "Persistence Follow-up: COTF Ch09 Scarlet Final Gear".

## Custom Item Name Resolution

For custom campaign equipment, the item name may not be obvious from the rawcode alone.

1. Extract object/string files from the live archive: check campaign-level `war3campaign.w3t` / `war3campaign.wts` and map-level `war3map.w3t` / `war3map.wts`.
2. Search the relevant `.wts` file for the displayed item name and note the `STRING <id>`.
3. Search the matching `.w3t` file for `TRIGSTR_<id>` to locate the custom item object.
4. Read the nearby 4-byte item rawcode and verify it appears in the decoded source save.
5. Convert raw bytes to the JASS literal using the FourCC reversal rule when this campaign requires it.

Example only, not a reusable default:

```text
Displayed item: 深渊领主的项链
war3campaign.wts: STRING 6368
war3campaign.w3t object: I60I
decoded save raw bytes: I06I
JASS literal: 'I60I'
runtime owner: Maiev owner 0x1845 near 0x5eb2a7
```

## Regression Example: Hatred Shadow 111

This example documents one confirmed successful migration. Use it to avoid repeating the same failure mode, not as a template inventory for other campaigns.

Decoded source cache / embedded `CommonCache.w3v` in `.tmp_111_live.raw.bin` can be stale. In this case it showed this cache view:

```text
Maiev raw bytes:   bonc, bonc, J06I, nehs, 1gar, ziwr
Anyndra raw bytes: dpsb, bonc, ziwr, 1edr, 1tsr, namp
```

For save `111.w3z` in this case, a narrow runtime owner scan over only `0x5c0000-0x5d0000` was incomplete. A full raw scan is required because Maiev's custom campaign items appeared later in the decoded save (`G06I` near `0x5d5733`, `I06I` near `0x5eb265`).

Full runtime-held source inventory:

```text
Maiev owner 0x1845:   bonc, J06I, nehs, ziwr, G06I, I06I
Anyndra owner 0x189c: 1nir, bonc, 1gar, dpsb, bonc, ziwr
Not held by runtime:  1edr, 1tsr, namp
```

The complete runtime-derived JASS grant list used for the full chapter 4 patch:

```jass
call UnitAddItemById(u, 'cnob')
call UnitAddItemById(u, 'I60J')
call UnitAddItemById(u, 'shen')
call UnitAddItemById(u, 'rwiz')
call UnitAddItemById(u, 'I60I')
call UnitAddItemById(u, 'I60G')
```

```jass
call UnitAddItemById(u, 'rin1')
call UnitAddItemById(u, 'cnob')
call UnitAddItemById(u, 'rag1')
call UnitAddItemById(u, 'bspd')
call UnitAddItemById(u, 'cnob')
call UnitAddItemById(u, 'rwiz')
```

Confirmed successful live patch marker:

```text
OMX111 full runtime gear patch executed
```

Use the chapter entry point for verification. Do not verify from stale in-map saves after a map-script patch. For a different campaign, generate a new marker string and rediscover the source hero handles/items.

## Robust Migration Strategy

When direct `.w3v` editing fails or the target chapter still enters with empty inventory:

1. Patch the target chapter's `war3map.j`.
2. Add small helper functions after `endglobals` and before any caller.
3. Clear target hero inventory.
4. Add items by rawcode after the chapter has restored or created the heroes.
5. If timing is uncertain, apply once immediately after restore and once after a short `TriggerSleepAction`.
6. Add a temporary visible marker text such as `OMX inventory patch executed` so the user can confirm the patched script actually ran.

Remove or keep the marker based on user preference after the migration is stable.

## Failure Interpretation

- Marker does not appear: user is not running the patched campaign/map, or the trigger path did not execute.
- Marker appears but inventory is empty: wrong unit variable, later inventory clearing, invalid rawcodes, or custom item definitions unavailable in the target map.
- Chapter reports load error: JASS compile/load failure or corrupted MPQ map archive. Read `mpq-jass-patching.md`.
