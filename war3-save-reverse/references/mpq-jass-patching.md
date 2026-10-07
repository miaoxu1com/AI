# MPQ and JASS Campaign Patching

## Scope

Use this reference for `.w3n` custom campaigns, `.w3x` maps, `war3map.j`, and Warcraft III "load error" failures after a patch.

## Archive Relationship

Custom campaign:

```text
campaign.w3n
  Maiev04.w3x
    war3map.j
    war3map.w3u
    other map assets
```

Always patch the innermost file, rebuild the map archive, then replace the map archive inside the campaign archive.

## Tooling

Use SFMPQ helpers if no MPQ editor is installed. The bundled C sources are:

```text
scripts/sfmpq_extract.c
scripts/sfmpq_update.c
```

They load `sfmpq.dll` from `SFMPQ_DLL` if set. Otherwise they try common Warcraft/JassHelper paths. Compile with an available Windows C compiler, then run:

```powershell
.\sfmpq_extract.exe campaign.w3n out_campaign Maiev04.w3x
.\sfmpq_extract.exe out_campaign\Maiev04.w3x out_map war3map.j
.\sfmpq_update.exe out_campaign\Maiev04.w3x patched\war3map.j war3map.j
.\sfmpq_update.exe campaign.w3n out_campaign\Maiev04.w3x Maiev04.w3x
```

If a previously built helper is already known good in the workspace, reuse it but still verify by re-extraction.

## Safe Patch Procedure

```powershell
$campaign = "Campaigns\your-campaign.w3n"
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
Copy-Item -LiteralPath $campaign -Destination "$campaign.bak-$stamp-before-jass-patch" -Force

Remove-Item -Recurse -Force .tmp_campaign,.tmp_map -ErrorAction SilentlyContinue
.\sfmpq_extract.exe $campaign .tmp_campaign Maiev04.w3x
.\sfmpq_extract.exe .tmp_campaign\Maiev04.w3x .tmp_map war3map.j

# edit .tmp_map\war3map.j

Copy-Item .tmp_campaign\Maiev04.w3x .tmp_Maiev04.patched.w3x -Force
.\sfmpq_update.exe .tmp_Maiev04.patched.w3x .tmp_map\war3map.j war3map.j
.\sfmpq_update.exe $campaign .tmp_Maiev04.patched.w3x Maiev04.w3x
```

Verify:

```powershell
Remove-Item -Recurse -Force .tmp_verify_campaign,.tmp_verify_map -ErrorAction SilentlyContinue
.\sfmpq_extract.exe $campaign .tmp_verify_campaign Maiev04.w3x
.\sfmpq_extract.exe .tmp_verify_campaign\Maiev04.w3x .tmp_verify_map war3map.j
(Get-FileHash .tmp_verify_map\war3map.j).Hash -eq (Get-FileHash .tmp_map\war3map.j).Hash
Select-String -Path .tmp_verify_map\war3map.j -Pattern "your marker|function YourPatch"
```

## JASS Rules That Cause Load Error

Warcraft may show only "load error" when the map script fails. Check these before blaming MPQ:

- No forward calls: define helper functions before any function that calls them. A safe insertion point is immediately after standalone-line `endglobals`.
- When locating `endglobals`, match the complete non-comment line, for example `(?m)^[ \t]*endglobals[ \t]*(?:\r?\n|\r)`. Do not use broad substring search because generated scripts can contain comments such as `//endglobals ...`.
- No duplicate function names.
- Keep inserted helper names short. Older Warcraft III JASS compilers can fail on long
  identifiers and then report a cascade of unrelated "undeclared identifier" errors in
  later generated code. Prefer compact unique prefixes such as `OMX_AJMI_*` instead of
  long names such as `OMX_AllianceAshJudgmentMagicImmune_*`.
- `local` declarations must be at the top of the function before executable statements.
- Rawcode literals must be valid 4-character constants, for example `'cnob'`.
- Do not insert helper functions inside `globals ... endglobals` or inside another function.
- Avoid adding dependencies on unavailable BJ/native wrappers unless the map already uses them.
- For Reforged damage modifiers, prefer the pre-damage event plus `BlzSetEventDamage` when the goal is to change the same damage instance. Do not simulate a percentage modifier with an extra `UnitDamageTarget` hit unless the design really wants a second damage event; it can recurse, use different armor/resistance rules, and show misleading results.

## Inventory Patch Template

Place helper functions after `endglobals`:

```jass
function OMX_ClearInventory takes unit u returns nothing
    local integer i=0
    local item it
    loop
        exitwhen i >= 6
        set it=UnitItemInSlot(u, i)
        if ( it != null ) then
            call RemoveItem(it)
        endif
        set i=i + 1
    endloop
    set it=null
endfunction

function OMX_Grant111Maiev takes unit u returns nothing
    if ( u == null ) then
        return
    endif
    call OMX_ClearInventory(u)
    call UnitAddItemById(u, 'cnob')
    call UnitAddItemById(u, 'cnob')
    call UnitAddItemById(u, 'I60J')
    call UnitAddItemById(u, 'shen')
    call UnitAddItemById(u, 'rag1')
    call UnitAddItemById(u, 'rwiz')
endfunction
```

Call the grant function only after the hero variable is assigned/restored. If the map has a startup trigger like `InitialDialog`, insert after the restore/create calls and before the function ends.

## Recovery From Load Error

1. Restore the newest `before-...` backup.
2. Re-apply a smaller patch.
3. Remove `TriggerSleepAction` and marker text if the target function may not tolerate sleeps.
4. Move helper definitions directly after `endglobals`.
5. If still failing, patch only a diagnostic `DisplayTimedTextToForce` first to confirm JASS loadability.

Do not continue stacking patches on a broken `.w3n`; restart from a clean backup or a verified pre-patch copy.

## Reforged MPQ Attribute Trap

If a Reforged custom campaign still shows "load error" after the JASS syntax and function order look valid, inspect MPQ file attributes before changing more script. Community guidance for Warcraft III map crashes after `war3map.j` replacement is to keep the archive entry attributes exactly the same: compressed, encrypted, delete marker, sector CRC, and single-unit.

For `.w3n` campaigns, preserve attributes at both layers:

1. Record the original campaign entry flags for the chapter map, for example `5.w3x`.
2. Record the original inner map entry flags for `war3map.j`.
3. Replace `war3map.j` inside the `.w3x` using the same compression/storage flags.
4. Replace the `.w3x` inside the `.w3n` using the same campaign-entry flags.
5. Re-extract the live `.w3n`, confirm all maps extract, and compare the changed entries' flags plus script markers.

A confirmed failure pattern: a chapter map stored uncompressed in the campaign (`flags=0x80000000`, compressed size equals file size) was reinserted with zlib compression (`flags=0x80000200`). The inner `war3map.j` extracted and parsed, but Reforged could not enter the chapter. The fix was to roll back to a known-good campaign and reapply the script patch while preserving the original outer `.w3x` storage flag.

Use a no-op test when repeated load errors occur: extract a chapter, replace `war3map.j` with byte-identical content, reinsert the chapter with preserved flags, then ask for a game test only after extraction and flag checks pass. If the no-op replacement fails, the problem is the MPQ update method rather than JASS.

Do not use a helper that always adds `MPQ_FILE_COMPRESS` for every replacement. For each file, copy only the original flags that matter for storage: `MPQ_FILE_COMPRESS`, `MPQ_FILE_IMPLODE`, `MPQ_FILE_ENCRYPTED`, `MPQ_FILE_KEY_V2`, `MPQ_FILE_SINGLE_UNIT`, and `MPQ_FILE_SECTOR_CRC`, plus the replace-existing flag required by the update API.
