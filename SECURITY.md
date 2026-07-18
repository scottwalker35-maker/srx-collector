# Security Policy

## Credentials

The exporter requires NETCONF credentials for each SRX.

- Store live credentials only in `config.yaml`.
- Restrict access with:

  ```bash
  chmod 600 config.yaml
  ```

- Never commit `config.yaml`.
- Never place passwords in Python files, shell history, screenshots, or
  support tickets.
- Rotate any credential that has been shared outside the trusted
  environment.

## Junos account permissions

Use a dedicated monitoring account with only the permissions required to run
the operational RPCs used by the collectors.

Do not use a full administrative account unless necessary for initial
testing.

## Network exposure

- Restrict TCP/830 so only the exporter host can reach NETCONF.
- Restrict TCP/9105 so only Prometheus or trusted management systems can
  scrape the exporter.
- The built-in HTTP endpoint does not provide authentication or encryption.
  Use host firewall rules, network segmentation, or a reverse proxy where
  required.

## SSH host keys

The current NETCONF client uses `hostkey_verify=False`. This is convenient in
a lab but is not ideal for untrusted networks. Production deployments should
consider known-host validation.

## Reporting a vulnerability

Do not include passwords, private keys, live configurations, or internal IP
details in a public report.
