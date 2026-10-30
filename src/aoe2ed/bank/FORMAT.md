# Player.nfp campaign bank format

`<profile>/profile/Player.nfp` (for example
`%USERPROFILE%\Games\Age of Empires 2 DE\<steamid>\profile\Player.nfp`) holds the player's
profile: hotkey file names, recent RMS maps, lobby settings, player names and so on. It also
holds the campaign key-value bank that the scenario effects **Store Key Value**, **Load Key Value**
and **Delete Key** read and write.

The format was worked out from a real profile (build with header float 7.8, about 5 KB
compressed and 41 KB raw, holding 194 bank entries from the official campaigns pacam1, prcam1,
3kcam1-3, sacam1-3 and nocam1-3, plus test campaigns). Only the bank section is interpreted.
Everything else is carried through as opaque bytes.

## Compression

The whole file is a single **raw DEFLATE** stream: no zlib header, no gzip header, no trailer.

```python
raw = zlib.decompress(data, -15)
```

The game's encoder is not zlib's. None of the zlib level, memLevel or strategy combinations
reproduce the original bytes. So:

- An **unchanged** bank is written back as the original compressed bytes (byte-identical).
- A **changed** bank is recompressed with `zlib` level 9, raw deflate. Any conforming inflater,
  including the game's, reads it. It just won't match what the game itself would have written.

No length, offset, CRC or Adler checksum anywhere in the file covers the bank section. A search
for the raw length, the section bounds and the CRC32/Adler32 found nothing. So the section can
grow or shrink freely.

## Raw layout

All integers are little-endian.

```
offset 0   f32  7.8        format/version (observed)
       4   f32  1123.0     (unknown)
       ...                 profile data (opaque)
       S-8 u64  123456     constant that immediately precedes the bank (also appears once earlier)
       S   u32  count      number of bank records
       S+4 record[count]
       E   ...             more profile data (opaque; starts ff ff ff ff 02 00 00 00 in the sample)

record:
       u64  name_len
       u8   name[name_len]   UTF-8, "PKEY:<campaign>:<key>", not NUL-terminated
       i64  value
```

- `<campaign>` is the campaign's internal name: the official ones use `3kcam1`, `pacam1` and so
  on, and custom campaigns use their `.aoe2campaign` file name without the extension. It may
  contain spaces (`KV Test`). It is the text between the first and second `:`.
- `<key>` is everything after the second `:`. Official keys contain `(`, `)`, `/`, `.`, spaces
  and non-ASCII characters (3kcam2 has both `LuBuRecruited(1)Yes(2)No` and
  `LüBuRecruited(1)Yes(2)No`).
- Values are signed 64-bit.
- Record order looks like hash-table iteration order for old entries, with keys stored in the
  current session appended at the end. The editor keeps the existing order, updates values in
  place, appends new keys and removes deleted records.

## Locating the section

1. Find the first occurrence of `PKEY:`. The record count sits 12 bytes before it (`u32 count` +
   `u64 name_len`). Parse `count` records from there. The parse must stay in bounds, and every
   name must start with `PKEY:`.
2. If there is no `PKEY:` (an empty bank), take the last occurrence of the u64 `123456` that is
   directly followed by a `u32 0`.

Step 2 is an inference from the sample: an empty bank hasn't been observed from the game itself.
Test campaigns should keep at least one key if that matters.

## Safety rules the editor enforces

- The game loads the profile at start-up and rewrites `Player.nfp` when it exits. Edits made
  while `AoE2DE_s.exe` runs are lost, and they can also clobber the game's own writes. `save()`
  refuses while the game is running.
- `save()` copies the existing target to `Player.nfp.<YYYYmmdd-HHMMSS>.bak` before writing,
  writes through a temporary file plus `os.replace`, and re-parses the new bytes before writing
  anything.

## Not yet verified in game

- That the game loads a file recompressed by zlib. It should, because it is plain DEFLATE, but
  no in-game run has confirmed it yet.
- Whether the game accepts `:` inside a key (the editor allows it, but forbids `:` in the
  campaign name).
