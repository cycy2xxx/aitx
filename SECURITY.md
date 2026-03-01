# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 0.1.x | Yes |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT open a public GitHub issue** for security vulnerabilities.
2. Email the maintainers or use [GitHub's private vulnerability reporting](https://github.com/cycy2xxx/aitx/security/advisories/new).
3. Include a description of the vulnerability, steps to reproduce, and potential impact.
4. We will acknowledge receipt within 48 hours and provide a timeline for a fix.

## Security Considerations

### Mesh Network

The P2P mesh network (`aitx.mesh`) uses mDNS for zero-config discovery on the local network. Important security notes:

- **No authentication by default.** Any device on the same LAN can discover and execute tools exposed via `serve_mesh()` or `MeshNode`.
- **Use only in trusted environments** (development machines, private networks).
- **Do not expose mesh nodes to the public internet** without additional security measures.
- Authentication support is planned for a future release.

### Tool Execution

- `aitx.handle_*()` functions execute Python functions with arguments provided by the LLM. Ensure your tool functions validate inputs appropriately.
- The dispatch engine catches exceptions and returns them as error results, but does not sandbox execution.

### Schema Conversion

- Schema conversion (`aitx.convert()`) is a pure data transformation with no code execution or network access.
