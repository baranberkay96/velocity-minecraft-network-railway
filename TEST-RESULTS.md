# Local verification — 2026-11-21

All checks below used local Docker Desktop, explicit `--platform linux/amd64`, `--init`, two isolated test containers, separate named volumes, and a private Docker network. The host architecture is aarch64, so the amd64 runtime was emulated; this is not a native amd64 performance benchmark. No cloud project was created for these checks. EULA=true was used only for the local runtime test under the user's existing acceptance; the template still defaults EULA to blank.

| Check | Observed result |
|---|---|
| Build Velocity Dockerfile | PASS, linux/amd64; fixed Velocity 4.3.1 build 45 JAR SHA-256 verified |
| Build Paper Dockerfile | PASS, linux/amd64; fixed Paper 26.3 build 257 JAR SHA-256 verified |
| Runtime | Eclipse Temurin Java 25; Paper startup completed and saved its world |
| Image size | Velocity 163,095,460 bytes; Paper 180,307,489 bytes reported by Docker (well below the 4 GB compressed limit even as unpacked images) |
| Test suite | 13 tests PASS in the image's actual Python + PyYAML runtime |
| Private proxy status | PASS, `Paper 26.3`, protocol 777, 0/20 players, backend description passed through |
| Public local TCP proxy | PASS from host to 127.0.0.1:27565; same Paper status; backend had no published port |
| Direct backend login, ordinary client | PASS: Paper requested `velocity:player_info`, then disconnected: “This server requires you to connect with Velocity.” |
| Direct backend login, forged signature | PASS: a zero-filled forwarding MAC was rejected with “Unable to verify player details” |
| Forwarding settings | PASS: both stored secret digests matched; Paper's enabled and online-mode forwarding settings true; secret file mode 0600 |
| No privilege grants | PASS: live Paper `ops.json` and `whitelist.json` were both empty arrays |
| Stored secret typo | PASS: invalid replacement retained the original valid secret; missing initial secret generated and persisted a private random value |
| Invalid non-secret fields | PASS: invalid numeric fields used defaults; invalid whitelist switch enabled whitelist; MOTD newline did not inject a properties entry |
| EULA not accepted | PASS: `/health` HTTP 200 with blocked reason, `/ready` 503, no EULA acceptance file, no game listener |
| Paper under 512 MiB cap | PASS: blocked health status with plan/memory guidance, `/ready` 503, no game listener, no restart loop |
| Graceful shutdown | PASS: logs recorded dimension saves and completed region-file I/O |
| Container replacement/restart persistence | PASS: same volume loaded again; identical SHA-256 of all three dimensions' saved `world_gen_settings.dat` files, level.dat present, 13 region/entity files remained; subsequent proxy status and rejection checks passed |
| Protocol-based startup readiness | PASS: both real services returned `/health` HTTP 503 with starting state, then HTTP 200 after valid Minecraft status became available |
| Private lobby outage | PASS: stopping Paper changed Velocity `/health` and `/ready` to HTTP 503 while Velocity remained running and its public TCP listener stayed open |
| Invalid Minecraft status | PASS: socket tests reject non-Minecraft, empty, oversized VarInt/packet, malformed JSON, incomplete schema, and truncated responses; unready HTTP state returns 503 |
| Post-restart private readiness | PASS: `/ready` HTTP 200 for both services; Velocity compares its status with the reachable private Paper backend |

Short idle observation after boot: Lobby approximately **1.0 GiB** under a **3 GiB** cap; Velocity approximately **292–298 MiB** under a **1 GiB** cap. No players joined during measurement. These figures do not establish loaded-world capacity; recommend 3–4 GB container RAM for Paper and about 1 GB for Velocity.

The initial host-only unittest attempt lacked PyYAML and the host sandbox denied socket listeners; the complete suite was then run successfully inside the deployable image, which installs that dependency. Early status probes ran before world generation completed and correctly found the backend not yet listening; all final status and rejection probes passed. The readiness fix also covers private-backend mismatch and immediate child death with HTTP checks. Paper 26.3 stores world generation settings per dimension instead of the older level.dat/WorldGenSettings layout; the persistence probe uses the observed current files.

Not verified: Railway cloud DNS and allocated TCP ingress, authenticated gameplay with a paid Minecraft account, player-driven server switching, plugin compatibility, long-duration load, or offsite restoration. The tests prove status routing, backend identity verification, configuration safety, and saved world reuse; they do not claim a full authenticated player join.

## Reproduce

```sh
docker build --platform linux/amd64 -t local/railway-velocity:4.3.1 services/velocity
docker build --platform linux/amd64 -t local/railway-paper:26.3 services/paper
docker run --rm --platform linux/amd64 --entrypoint python3 -v "$PWD:/test:ro" local/railway-paper:26.3 -m unittest discover -s /test/tests -v
```

Run `tests/protocol_probe.py proxy.railway.internal lobby.railway.internal` from a Python-equipped container on the same private network, after Paper reports `Done`. Both addresses must resolve privately on that network. Set both services' EULA and shared secret explicitly for an authorized runtime test. The protocol probe creates no account and grants no permissions.
