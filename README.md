# WPP

## Requirements

- [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) (requires [WSL](https://learn.microsoft.com/en-us/windows/wsl/install))
- [Make](https://community.chocolatey.org/packages/make) via [Chocolatey](https://chocolatey.org/install)

### Installing Make (Windows)

1. Open CMD/PowerShell **as Administrator**
2. Install Chocolatey: https://chocolatey.org/install
3. Then run: `choco install make`

## Run

```bash
cp .env.example .env
make dev-up
```

- Frontend: http://localhost:3071
- Backend: http://localhost:8037/docs
