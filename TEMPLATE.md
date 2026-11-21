# Velocity Minecraft Network (Paper Lobby)

Repository to publish later: `baranberkay96/velocity-minecraft-network-railway`. This package was assembled and tested locally; cloud checks are pending root integration.

## Composer specification

Use `template.json` as the canonical machine-readable service and variable specification. Add two repo services: Velocity from `/services/velocity`, Lobby from `/services/paper`. Give each a separate `/data` volume and one replica. Both use private `/health`, port 8080, 1200-second health window, restart ALWAYS, 120-second draining and zero overlap. Velocity alone has TCP Proxy to internal 25565. Neither service has a public HTTP domain. Lobby has no TCP Proxy.

Lobby `EULA` is the only required user field and defaults to blank. The user must enter `true` after accepting the EULA. Velocity references Lobby's acceptance. Lobby generates `FORWARDING_SECRET` with `${{secret(64)}}`; Velocity references `${{Lobby.FORWARDING_SECRET}}`. Its backend address is `${{Lobby.RAILWAY_PRIVATE_DOMAIN}}`, resolved when connections occur rather than blocking initial startup on DNS. The two services can start in either order.

Minecraft account authentication is permanently enabled on Velocity. Paper is deliberately offline behind the private network and requires authenticated modern forwarding. Paper's `proxies.velocity.online-mode=true` matches the authenticated proxy. RCON, UDP query, HAProxy protocol, legacy BungeeCord forwarding, and public backend ingress are disabled. No account receives operator privileges. Optional whitelist is controlled by `WHITELIST_ENABLED`; its account list persists on the Paper volume.

Every exposed variable and its description/default are in template.json. Server security fields are managed at each startup. Other Paper YAML configuration persists. Extra proxy backends use `/data/backends.json` with validated Railway-private hostnames; their worlds each need their own service and volume. Configuration values that cannot be parsed use safe defaults. Invalid credentials preserve a valid stored secret or create an unshared random secret, closing backend logins. Missing EULA/undersized container remains alive with private HTTP 200 blocked status and no game process, rather than restarting indefinitely. `/health` otherwise returns 503 until a valid bounded Minecraft status response is received. Velocity additionally requires private Lobby status and matching version/description through the proxy; an open TCP port is insufficient. `/ready` returns 503 for every blocked or unready state. Shutdown immediately clears readiness, and the HTTP handler checks child-process liveness.

## Version pins (2026-11-21)

- Velocity **4.3.1 build 45**, stable channel; fixed official artifact URL and SHA-256 in Dockerfile.
- Paper **26.3 build 257**, stable channel; fixed official artifact URL and SHA-256 in Dockerfile.
- Eclipse Temurin **25.0.5.1_2-jre-noble**, fixed image index digest. Both services run Java 25, as current official upstream requires.

See NOTICE.md for exact checksums and source links. There is no floating latest download API in the images.

## Improvements over market templates

No standalone Velocity marketplace package was found in the current audit; WebbMC is a broader server panel. This purpose-built package provides a real Paper lobby rather than an external-server placeholder, online account verification at the proxy, a generated shared modern-forwarding secret, private-only backend routing, independent persistent worlds, explicit EULA acceptance, cautious input validation, graceful Java shutdown, and pinned verified artifacts. Packaging conventions were checked against the existing Minecraft and Horizon packages without copying their source or prose.

## Resource profile and cost

Use **Hobby minimum**; Trial's 1 GB/service and Free's 0.5 GB/service cannot run the complete Paper network. The supervisor blocks the Paper game process below 1536 MiB rather than promising a usable low-memory server. Allocate **3–4 GB Lobby** and **about 1 GB Velocity**; actual consumption is workload-dependent. No plugins are bundled.

| Service | Estimated idle RAM | Small active group RAM | CPU guidance |
|---|---|---|---|
| Velocity | 150–350 MiB | 250–600 MiB | Usually low; allow 0.1–0.5 vCPU average |
| Lobby | 1.0–1.8 GiB | 1.8–3.2 GiB | 0.2–1 vCPU average; world generation can saturate 2 vCPU |

These estimates are not a player-capacity guarantee. Heap is capped below the container limit with native-memory headroom, and Java sees two processors to avoid oversizing host-derived thread pools. Default max players 20 is an admission limit, not a performance guarantee. Start with view distance 6/simulation distance 4 and adjust using real tick-time measurements.

Example monthly usage at RAM $10/GB-month, CPU $20/vCPU-month, volumes $0.15/GB-month: **3 GB average combined RAM + 0.5 vCPU average + 10 GB stored = $41.50/month**, plus network egress and any applicable plan minimum. A small network may use roughly $25–$65/month before traffic; populated worlds and plugins can cost more. Hobby volumes start at 5 GB per service; monitor world growth and upgrade storage/plan before filling the disk. The two volumes are not offsite backups.

## Local verification

See `TEST-RESULTS.md` for actual build and protocol observations. `python3 -m unittest discover -s tests -v` exercises security and typo handling. `tests/protocol_probe.py` runs from a container on the private network and compares proxy/backend status, then attempts a direct login without valid forwarding. It never authenticates a paid player account.

## Verification checklist

- Build both Dockerfiles for linux/amd64; check pinned artifact SHA-256 verification.
- Enter an explicit accepted EULA value and wait for Paper's `Done` log; `/ready` should become 200.
- Connect using Velocity's allocated public TCP hostname and port with a licensed Minecraft 26.3 account.
- Confirm the proxy status matches the Paper server and private direct login without forwarding is rejected.
- Confirm only Velocity has public TCP ingress and Paper is private-only.
- Confirm forwarding secrets match without printing them, and invalid replacements preserve stored secrets.
- Stop/restart with the same volumes; confirm the world seed, level metadata, and world files remain.
- Test whitelist changes with intended real account UUIDs and no unintended operator accounts.
- Export backups of both volumes; test restoration in a separate environment before upgrading.
- Verify missing EULA and low-memory tests show blocked status with no Java process and no game listener.

## Open questions

- Cloud checks are pending root integration; Railway private DNS/ingress remain to be verified there.
- Full authenticated gameplay requires a real paid Minecraft account and was not tested by the protocol probes.
- Plugin compatibility, large player counts, long-term world growth, and offsite backup operations remain operator-specific.
