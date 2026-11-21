# Railway cloud validation — 2026-11-21

These checks used isolated projects. Credentials were kept in memory. Test addresses are temporary.

## velocity-cloud-status

```json
{
  "version": {
    "protocol": 777,
    "name": "Paper 26.3"
  },
  "players": {
    "online": 0,
    "max": 20
  },
  "description": "A Minecraft network on Railway"
}
```

## velocity-cloud-redeploy

```json
{
  "version": {
    "protocol": 777,
    "name": "Paper 26.3"
  },
  "players": {
    "online": 0,
    "max": 20
  },
  "description": "A Minecraft network on Railway"
}
```

## velocity-postpublished

```json
{
  "templateId": "b402d254-213e-4b21-815f-b91a58c2d914",
  "code": "velocity-minecraft-network-paper-lobby",
  "services": [
    {
      "serviceName": "Lobby",
      "healthcheckPath": "/health",
      "latestDeployment": {
        "id": "8746302f-50c2-4b70-aece-463fce5a7d1f",
        "status": "SUCCESS"
      },
      "domains": {
        "serviceDomains": []
      }
    },
    {
      "serviceName": "Velocity",
      "healthcheckPath": "/health",
      "latestDeployment": {
        "id": "eaa98393-523b-4f91-911c-7c16a1ac2e8c",
        "status": "SUCCESS"
      },
      "domains": {
        "serviceDomains": []
      }
    }
  ],
  "public_status": {
    "version": {
      "protocol": 777,
      "name": "Paper 26.3"
    },
    "players": {
      "online": 0,
      "max": 20
    },
    "description": "A Minecraft network on Railway"
  },
  "online_auth_encryption_challenge": 1,
  "result": "PASS",
  "limitation": "No paid Minecraft account was authenticated."
}
```

Full authenticated gameplay with a paid Minecraft account was not tested.
