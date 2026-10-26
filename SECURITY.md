# Security

PolarWatch Web Monitor makes user-initiated HTTP(S), DNS and TLS requests to websites the user adds. It is a local desktop application, not a vulnerability scanner or an uptime service.

- No login, telemetry, database, server, wallet or cryptomining component.
- Site names and URLs are saved only in the user's local `sites.json`.
- Response times are kept in RAM during the current session; they are not proof of 24/7 uptime.
- Do not add private passwords, authentication tokens or secret URLs.
- Security-header presence alone is not a security audit.
- Untrusted websites should not be assumed safe just because they return HTTP 200.
- The distributed executables are not signed. Do not disable operating-system security protections to launch them.

**Report vulnerabilities privately to:** info@polarlabs.it. Avoid public issues for vulnerability details.
