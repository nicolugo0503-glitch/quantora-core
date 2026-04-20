# Quantora GitHub Deploy Hardening

This package includes:
- a Dockerfile that tolerates nested upload contexts during platform deploys
- a GitHub Actions workflow at `.github/workflows/docker-build.yml`
- deploy scripts for Windows and Mac

## GitHub Deploy

### Mac
```bash
./0_DEPLOY_TO_GITHUB.command
```

### Windows
Run:
```bat
0_DEPLOY_TO_GITHUB.bat
```

## What the workflow does
On every push to `main`, GitHub Actions builds the Docker image to catch broken deploy contexts before platform deploy.
