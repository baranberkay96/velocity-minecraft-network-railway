FROM eclipse-temurin:25.0.5.1_2-jre-noble@sha256:2ec98aa522c472deadfd2b7c5b39bca680e33ef522a53a72f10789bdf89a6bb5
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-yaml curl ca-certificates util-linux && rm -rf /var/lib/apt/lists/* && mkdir -p /opt/server /data
RUN curl -fsSL --retry 5 --retry-all-errors -A 'railway-velocity-network/1.0 (https://github.com/baranberkay96/velocity-minecraft-network-railway)' 'https://fill-data.papermc.io/v1/objects/64a5bd44910cb982b2648e9a35036cc95a6de4d561e15812aecf5411f84f7b01/paper-26.3-257.jar' -o /opt/server/paper.jar && echo '64a5bd44910cb982b2648e9a35036cc95a6de4d561e15812aecf5411f84f7b01  /opt/server/paper.jar' | sha256sum -c -
COPY launch.py /opt/server/launch.py
COPY --chmod=0755 entrypoint.sh /opt/server/entrypoint.sh
ENV SERVER_ROLE=paper PORT=8080
WORKDIR /data
EXPOSE 25565/tcp 8080/tcp
ENTRYPOINT ["/opt/server/entrypoint.sh"]
