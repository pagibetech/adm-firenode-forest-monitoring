# Raspberry Pi Automated Deployment

Last updated: 2026-05-20

This guide deploys the ADM FireNode Raspberry Pi app from the MacBook to the four Raspberry Pis using SSH key authentication.

ESP32 and LoRa hardware validation is paused for this phase. The deployed Raspberry Pi app is configured in simulation mode.

## Targets

| Role | Hostname | IP |
| --- | --- | --- |
| Main Server | `node-main-center` | `192.168.9.51` |
| Node 1 | `node-01` | `192.168.9.52` |
| Node 2 | `node-02` | `192.168.9.53` |
| Node 3 | `node-03` | `192.168.9.54` |

SSH user: `betech`

SSH private key on MacBook: `~/admfire`

Remote app folder: `/home/betech/admfire/raspi/firenode-system`

## What The Scripts Do

- SSH into each Raspberry Pi using key auth.
- Install `rsync` if needed.
- Copy the Raspberry Pi app package to the target.
- Run the existing Raspberry Pi setup script in manual-start mode.
- Create/update the Python virtual environment.
- Install Python requirements.
- Write node-specific `config.json` values.
- Enable simulation mode.
- Set the node role, node IP, main server IP, and remote node IP list.
- Create an optional `firenode-rpi.service` systemd unit.
- Keep manual start as the default unless `--install-service` is used.

## Deploy Everything

From the MacBook:

```bash
cd "/Users/macbookm1max321tb/A_Design/A_Coding/ADM Fire"
chmod +x scripts/deploy_main_server.sh scripts/deploy_node.sh scripts/deploy_all_rpis.sh
./scripts/deploy_all_rpis.sh
```

This does not require ESP32 or LoRa hardware.

## Deploy One Raspberry Pi

Main server:

```bash
./scripts/deploy_main_server.sh
```

One remote node:

```bash
./scripts/deploy_node.sh node-01 192.168.9.52 node 192.168.9.51
```

## Optional Flags

Install and start the optional systemd service:

```bash
./scripts/deploy_all_rpis.sh --install-service
```

Start the app once with `nohup` after deployment:

```bash
./scripts/deploy_all_rpis.sh --start
```

Run lightweight validation after deployment:

```bash
./scripts/deploy_all_rpis.sh --validate
```

If dependencies are already installed and only files/configs need updating:

```bash
./scripts/deploy_all_rpis.sh --skip-setup
```

## Manual Start

Manual start remains the default.

Main server:

```bash
ssh -i ~/admfire betech@192.168.9.51
cd /home/betech/admfire/raspi/firenode-system
./run.sh
```

Node 1:

```bash
ssh -i ~/admfire betech@192.168.9.52
cd /home/betech/admfire/raspi/firenode-system
./run.sh
```

Repeat for Node 2 and Node 3 using `192.168.9.53` and `192.168.9.54`.

## Service Checks

The deployment creates the service file, but does not enable it by default.

Check service status:

```bash
ssh -i ~/admfire betech@192.168.9.51 'sudo systemctl status firenode-rpi --no-pager'
```

Enable and start service later:

```bash
ssh -i ~/admfire betech@192.168.9.51 'sudo systemctl enable --now firenode-rpi'
```

Stop and disable service:

```bash
ssh -i ~/admfire betech@192.168.9.51 'sudo systemctl disable --now firenode-rpi'
```

View logs:

```bash
ssh -i ~/admfire betech@192.168.9.51 'sudo journalctl -u firenode-rpi -f'
```

## Flask/API Checks

After starting the app:

```bash
curl http://192.168.9.51:8090/api/status
curl http://192.168.9.51:8090/api/config
curl http://192.168.9.51:8090/api/server-dashboard
curl http://192.168.9.51:8090/api/lora/status
```

Node checks:

```bash
curl http://192.168.9.52:8090/api/status
curl http://192.168.9.52:8090/api/node-data
curl http://192.168.9.53:8090/api/node-data
curl http://192.168.9.54:8090/api/node-data
```

## Simulation Mode Checks

Confirm simulation mode:

```bash
ssh -i ~/admfire betech@192.168.9.51 'python3 -m json.tool /home/betech/admfire/raspi/firenode-system/config.json | grep -E "role|operation_mode|thermal_simulation|remote_node_ips"'
ssh -i ~/admfire betech@192.168.9.52 'python3 -m json.tool /home/betech/admfire/raspi/firenode-system/config.json | grep -E "role|operation_mode|main_server_ip"'
```

Expected:

- Main server role is `server`.
- Remote nodes use role `node`.
- `operation_mode` is `simulation`.
- Main server has remote node IPs `192.168.9.52`, `192.168.9.53`, `192.168.9.54`.
- Main server thermal camera uses `thermal_simulation: true` until MLX90640 live validation resumes.

## Stream Placeholder Checks

Camera feed headers:

```bash
curl -I --max-time 5 http://192.168.9.51:8090/video_feed
curl -I --max-time 5 http://192.168.9.52:8090/video_feed
```

Main thermal placeholder PNG:

```bash
curl --output /tmp/firenode-thermal.png http://192.168.9.51:8090/thermal.png
file /tmp/firenode-thermal.png
```

Open the dashboard:

```text
http://192.168.9.51:8090
```

## Troubleshooting

If SSH fails:

```bash
ssh -i ~/admfire betech@192.168.9.51
```

If apt asks for a password, enter the Raspberry Pi password for `betech`.

If the app does not start:

```bash
ssh -i ~/admfire betech@192.168.9.51
cd /home/betech/admfire/raspi/firenode-system
./run.sh
```

If port `8090` is already in use:

```bash
ssh -i ~/admfire betech@192.168.9.51 'sudo lsof -i :8090 || true'
```
