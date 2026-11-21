# Deploy and Host Velocity Minecraft Network (Paper Lobby) with Railway

Deploy a community Minecraft Java Edition network with Velocity 4.3.1 and a working Paper 26.3 lobby. Players connect to one public TCP address. The lobby stays on Railway's private network, with authenticated modern forwarding and persistent worlds. Explicit Minecraft EULA acceptance and a paid Minecraft account for players are required.

## About Hosting Velocity Minecraft Network (Paper Lobby)

Velocity authenticates players with Minecraft's account services and forwards their identity to the Paper lobby using a generated shared secret. The lobby runs in offline mode specifically for this proxy arrangement; it has no public TCP proxy or public HTTP domain. Both services use Java 25 and separate persistent volumes. Paper creates a playable survival world on first start. You can later add compatible Paper servers as private backends. This is a small complete network, with no bundled web panel, arbitrary operator accounts, or plugins that you must configure before playing.

## Common Use Cases

- A community lobby with a single stable connection address.
- A survival world behind an authenticated Minecraft proxy.
- A starting point for multiple Paper worlds or game modes.
- A private group server with Paper's optional whitelist.

## Dependencies for Velocity Minecraft Network (Paper Lobby) Hosting

- Railway Hobby or higher; allocate 3–4 GB to Lobby and about 1 GB to Velocity. Trial/Free are unsuitable for this complete network.
- A Minecraft Java Edition client compatible with Paper 26.3 and a licensed account.
- Explicit acceptance of the Minecraft EULA by setting Lobby `EULA=true`.
- Only Velocity needs Railway TCP Proxy on internal port 25565. Use its allocated public hostname **and allocated port**, which is usually different from 25565.

### Deployment Dependencies

- [Velocity installation](https://docs.papermc.io/velocity/getting-started/)
- [Paper installation](https://docs.papermc.io/paper/getting-started/)
- [Modern player forwarding](https://docs.papermc.io/velocity/player-information-forwarding/)
- [Backend security](https://docs.papermc.io/velocity/security/)
- [Minecraft EULA](https://aka.ms/MinecraftEULA)

### Implementation Details

| Service | Purpose | Persistent data | Exposure |
|---|---|---|---|
| Velocity | Online account authentication and modern forwarding | `/data`: configuration, forwarding secret, proxy plugins | Public TCP 25565 through Railway; private health HTTP 8080 |
| Lobby | Paper 26.3 world and plugins | `/data`: worlds, player data, configuration, whitelist | Private TCP 25565 and health HTTP 8080 only |

1. Set Lobby `EULA=true` only after reviewing and accepting the EULA. Keep the generated `FORWARDING_SECRET`; Velocity references the same variable automatically.
2. Give Lobby 3–4 GB RAM and Velocity about 1 GB. Lobby's default Java heap is 2048 MiB; Velocity's is 384 MiB. Heap excludes native memory and filesystem cache.
3. Wait for Paper's `Done` log, then connect using Velocity's Railway TCP Proxy address. Paper downloads Mojang's server on first startup, so first boot takes longer.
4. No accounts receive operator privileges automatically. To enable a whitelist, set Lobby `WHITELIST_ENABLED=true` and maintain `/data/whitelist.json` with your intended accounts' real online UUIDs while Lobby is stopped. Keep `ops.json` empty unless you deliberately administer it yourself.

`/health` is a private supervisor status endpoint. It returns HTTP 200 with a blocked reason if the EULA is missing or container memory is below the startup floor, keeping a form mistake out of a restart loop. `/health` otherwise returns 503 until a valid Minecraft status response is available. `/ready` returns 503 for every blocked or unready state. Velocity also checks the private lobby and requires its own status response to match the lobby's version and description, so an open proxy port alone cannot pass readiness. Packet size and probe time are bounded. Check the logs before inviting players; these checks do not prove an authenticated player join.

**Additional backends:** duplicate Lobby with its own volume, the same forwarding secret and EULA setting, and no public networking. Put a JSON mapping such as `{"survival":"survival.railway.internal"}` in Velocity's `/data/backends.json` and redeploy Velocity. Entries accept private Railway hostnames only and use port 25565. The built-in lobby remains the initial destination. Configure trusted proxy plugins if you need player-driven server switching. Do not increase replicas for a world service or share world volumes.

**Configuration and secrets:** startup manages security settings, player/chunk limits, and the proxy routing file. Other existing Paper YAML settings are preserved. An invalid secret retains the stored value; on a fresh volume it generates an independent secret and backend authentication stays locked until both services have the same valid value. Secret values are never logged. Invalid numbers use defaults; an invalid whitelist switch enables the whitelist. Correct variables and redeploy to apply changes. Do not expose Lobby's port: private networking and the forwarding MAC provide separate protections.

**Persistence and upgrades:** stop services and back up both volumes before upgrading. Worlds and player data live in Lobby's volume; deleting that volume deletes the world. Change the fixed JAR URL and SHA-256 in each Dockerfile together, and update the pinned Java image when needed. Test plugins against the new versions in a separate environment. Upstream Paper or Mojang downloads still require internet access. There is no automatic offsite backup service in this template; export volume backups on your chosen schedule.

### Why Deploy Velocity Minecraft Network (Paper Lobby) on Railway?

Railway provides private service networking, generated variables, TCP ingress, and persistent volumes for a manageable two-service Minecraft network. Usage depends on world generation, players, plugins, storage, and traffic; budget for the complete Java processes, not just their heaps.
