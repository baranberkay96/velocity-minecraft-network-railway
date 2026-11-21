#!/usr/bin/env python3
"""Fingerprint persisted 26.3 world generation settings and chunk files."""
import hashlib
import json
from pathlib import Path

world = Path('/data/world')
generation = sorted(world.rglob('world_gen_settings.dat'))
assert len(generation) == 3, generation
assert (world / 'level.dat').stat().st_size > 0
print(json.dumps({'generation_sha256': {str(p.relative_to(world)): hashlib.sha256(p.read_bytes()).hexdigest() for p in generation},
                  'region_files': len(list(world.rglob('*.mca')))}, sort_keys=True))
