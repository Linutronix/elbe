Use the compression algorithm and level from Btrfs ``compress`` and
``compress-force`` mount options when populating images with
``mkfs.btrfs --rootdir``. This avoids exhausting partitions sized for compressed
data and requires btrfs-progs 6.13 or newer when compression is enabled.
Explicit ``--compress`` mkfs options take precedence. Compression uses the
mkfs heuristics, even when ``compress-force`` is configured.
