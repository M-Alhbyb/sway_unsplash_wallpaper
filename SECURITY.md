# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it by emailing the
project maintainers. Do **not** create a public GitHub issue.

Please include:

- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Potential impact

### What to expect

- Acknowledgment within 48 hours
- Regular updates on progress
- Disclosure after a fix is released

## Security Best Practices

### API Keys

- Your Unsplash API access key is stored in the local SQLite database at
  `~/.local/share/unsplash-wallpaper/database.db`
- The key is never transmitted to any server other than the official Unsplash API
- Log files automatically mask API keys in transit

### Data Storage

- All wallpaper data is stored locally in `~/.local/share/unsplash-wallpaper/`
- The database uses WAL mode for safe concurrent access
- Logs are rotated (max 1MB, 5 backups) to prevent disk exhaustion

### Network Security

- All API requests use HTTPS
- The application only connects to `api.unsplash.com`
- Download tracking follows Unsplash API guidelines

### Permissions

- The application runs as a user process, never as root
- Systemd services are installed per-user (`--user` scope)
- No elevated privileges are required or requested
