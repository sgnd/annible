# Contributing

Thanks for helping. Ansibro stays small and simple on purpose:
a beginner must be able to read every file. Use simple English.

## Suggest an app

Open an issue with the [Suggest an app](https://github.com/sgnd/ansibro/issues/new?template=suggest-an-app.yml) form. An app fits when all of these are true:

- It is open source, with an OSI-approved license (not BSL or SSPL).
- It has a multi-arch image (amd64 and arm64) with a pinned version.
- It works offline: everything it needs is in its image.
- Its category has fewer than two apps. Each category has two choices at most.

## Report a bug

Open an issue with the [Bug report](https://github.com/sgnd/ansibro/issues/new?template=bug-report.yml) form. For a security problem, see [SECURITY.md](SECURITY.md) instead.

## Add an app

1. Add it to [`catalog.yml`](catalog.yml) with its license and how to reach it.
2. Add its image to [`versions.yml`](versions.yml): tag and multi-arch digest
   (`docker buildx imagetools inspect <image>:<tag>`).
3. Copy a similar role: `roles/postgres/` for a server app, `roles/portainer/` for a swarm app.
   Do not use `ports:` in server apps. Published ports skip the firewall. Use `network_mode: host`.
4. Add it to the Apps table in the [README](README.md#apps), to [`THIRD_PARTY.md`](THIRD_PARTY.md), to
   [`config.example.yml`](config.example.yml), and a check to [`tests/check.py`](tests/check.py).
5. Test on a fresh server: run `./install.sh` two times (the second run must report `changed=0`),
   then `.venv/bin/python tests/check.py`.

**AI agents.** [`.claude/skills/`](.claude/skills) has skills for Claude Code and other agents
that read `SKILL.md`: set up `config.yml`, install, add an app, and update versions.

## Send a pull request

1. Make your change on a branch. `main` only takes changes from pull requests.
2. Run the checks. No servers needed. The first line makes `.venv/` with Ansible:

   ```bash
   ./install.sh config.example.yml --syntax-check
   .venv/bin/pip install ansible-lint==26.10.1
   .venv/bin/python tests/test_config.py      # config.example.yml works, mistakes are refused
   ANSIBRO_CONFIG=config.example.yml PATH="$PWD/.venv/bin:$PATH" ansible-lint --profile production
   shellcheck install.sh build-bundle.sh scripts/*.sh
   scripts/validate-versions.sh               # needs yq, docker and curl
   ```

3. Open the pull request. GitHub runs the same checks (see [`validate.yml`](.github/workflows/validate.yml)).
   They must pass before it can be merged.

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).
