# Sources and licensing

This package's launch scripts, Dockerfiles, tests, and prose were authored for this template. No files or README prose were copied from marketplace repositories. The local Minecraft and Horizon packages were consulted read-only for Railway packaging conventions. Root's marketplace audit found no standalone Velocity template; WebbMC's panel offering was reviewed as a broader competitor, not used as source code.

Official sources checked 2026-11-21:

- [Velocity 4.3.1 build 45 release metadata](https://fill.papermc.io/v3/projects/velocity/versions/4.3.1/builds): stable, published 2026-10-27; SHA-256 `0844bcabdcdb4f5b875906fd4c3365bc1bb76918e42bc595ed88ad195258dd75`.
- [Paper 26.3 build 257 metadata](https://fill.papermc.io/v3/projects/paper/versions/26.3/builds): stable, published 2026-11-20; SHA-256 `64a5bd44910cb982b2648e9a35036cc95a6de4d561e15812aecf5411f84f7b01`.
- [Velocity getting started](https://docs.papermc.io/velocity/getting-started/) and [Paper getting started](https://docs.papermc.io/paper/getting-started/): current Java 25 requirements.
- [Modern forwarding configuration](https://docs.papermc.io/velocity/player-information-forwarding/): proxy online mode, backend offline mode, Paper velocity enablement, matching secret, BungeeCord disabled.
- [Backend security](https://docs.papermc.io/velocity/security/): modern forwarding complements network isolation; do not expose backend ingress.
- [Velocity upstream](https://github.com/PaperMC/Velocity) is GPL-3.0 licensed. [Paper upstream](https://github.com/PaperMC/Paper) includes GPL-3.0 components and separately licensed patches; upstream notices remain in downloaded artifacts. Neither project is affiliated with this community template.
- [Eclipse Temurin official Docker tags](https://hub.docker.com/_/eclipse-temurin): `25.0.5.1_2-jre-noble`, index digest `sha256:2ec98aa522c472deadfd2b7c5b39bca680e33ef522a53a72f10789bdf89a6bb5` (checked using Docker Hub tag metadata). Temurin/OpenJDK and included OS packages retain their upstream licenses and notices in the image.
- The [Minecraft icon](https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/minecraft.svg) is linked from dashboard-icons and was checked to return HTTP 200. Minecraft names and artwork are trademarks of their owners.

The Docker build downloads official proxy/server launchers with SHA-256 verification. Paper's upstream launcher privately downloads Mojang's server on first startup. Minecraft is proprietary and subject to the [Minecraft EULA](https://aka.ms/MinecraftEULA); the template leaves acceptance blank and never assumes agreement. No Minecraft server JAR, world, credentials, or user account is included in this repository.
