FROM eclipse-temurin:25.0.5.1_2-jre-noble@sha256:2ec98aa522c472deadfd2b7c5b39bca680e33ef522a53a72f10789bdf89a6bb5
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-yaml curl ca-certificates util-linux && rm -rf /var/lib/apt/lists/* && mkdir -p /opt/server /data
RUN curl -fsSL --retry 5 --retry-all-errors -A 'railway-velocity-network/1.0 (https://github.com/baranberkay96/velocity-minecraft-network-railway)' 'https://fill-data.papermc.io/v1/objects/0844bcabdcdb4f5b875906fd4c3365bc1bb76918e42bc595ed88ad195258dd75/velocity-4.3.1-45.jar' -o /opt/server/velocity.jar && echo '0844bcabdcdb4f5b875906fd4c3365bc1bb76918e42bc595ed88ad195258dd75  /opt/server/velocity.jar' | sha256sum -c -
COPY launch.py /opt/server/launch.py
COPY --chmod=0755 entrypoint.sh /opt/server/entrypoint.sh
ENV SERVER_ROLE=velocity PORT=8080
WORKDIR /data
EXPOSE 25565/tcp 8080/tcp
ENTRYPOINT ["/opt/server/entrypoint.sh"]
