# Candy Home Assistant integration

[![Run tests](https://github.com/Mettyl/home-assistant-candy/actions/workflows/lint.yml/badge.svg)](https://github.com/Mettyl/home-assistant-candy/actions/workflows/lint.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)

An unofficial custom integration for locally connected Candy, Haier, and
Simply-Fi appliances. It reads appliance status directly over the local
network and can automatically determine the local protocol's encryption key
during setup.

This fork is based on
[bigmoby/home-assistant-candy](https://github.com/bigmoby/home-assistant-candy),
which is based on
[ofalvai/home-assistant-candy](https://github.com/ofalvai/home-assistant-candy).

> [!IMPORTANT]
> This project is not affiliated with, endorsed by, or supported by Candy,
> Haier, or their related companies. Write controls are experimental and have
> only been verified on the exact washing-machine model stated below. Use them
> at your own risk and never bypass the appliance's physical safety features.

## Features

- Local polling for washing machines, tumble dryers, dishwashers, and ovens.
- Automatic discovery and encryption detection during setup.
- Native Home Assistant sensors for state, cycle, remaining time, and
  appliance-specific values.
- Optional local controls verified on **Candy RO41274DWMSE/1-S**:
  - program, temperature, spin-speed, soil-level, and compatible washing-option
    selection;
  - start now or at a selected wall-clock time;
  - stop, pause, and resume;
  - post-cycle Refresh Touch.

Controls are disabled by default. The read-only integration remains available
for other supported appliances.

## Installation

### HACS custom repository

1. Install [HACS](https://hacs.xyz/docs/use/).
2. In HACS, open **Integrations**, then the menu and **Custom repositories**.
3. Add `https://github.com/Mettyl/home-assistant-candy` with category
   **Integration**.
4. Find **Candy Simply-Fi**, download it, and restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration**, search for
   **Candy**, and enter or select the appliance IP address.

### Manual

Copy `custom_components/candy` into the `custom_components` directory of your
Home Assistant configuration, restart Home Assistant, and add **Candy** from
**Settings → Devices & services**.

## Enabling washing-machine controls

Only do this for **Candy RO41274DWMSE/1-S**:

1. Open **Settings → Devices & services → Candy**.
2. Open **Configure** on the integration entry.
3. Read the warning and enable controls for `RO41274DWMSE/1-S`.
4. Reload the integration if Home Assistant does not do so automatically.

The appliance must still be placed in its physical remote-control mode. Home
Assistant cannot safely override the door lock, selector, or other hardware
interlocks. A scheduled start is sent to the appliance as a local delay, so it
continues even if Home Assistant later restarts.

## Standalone debugging tool

The helper in `tools/simplyfi.py` can inspect the same local API without Home
Assistant:

```bash
# Discover the local encryption key
python3 tools/simplyfi.py <APPLIANCE_IP> getkey

# Read the current appliance status
python3 tools/simplyfi.py <APPLIANCE_IP> <ENCRYPTION_KEY> read
```

Treat the encryption key as a password: do not paste it into issues, logs, or
commits. Status responses may also contain device-specific information, so
review them before publishing.

## Development

The development scripts target Linux or WSL. From the repository root:

```bash
make setup         # Create/update the development environment
make develop       # Start a local Home Assistant development instance
make check         # Ruff, mypy, and all tests
make lint          # Ruff and mypy only
make format        # Format integration and test code
make test          # Run tests
make test-coverage # Run tests with a coverage report
make clean         # Remove caches, build output, and the virtual environment
```

Please open bugs and model-support requests in this fork's
[issue tracker](https://github.com/Mettyl/home-assistant-candy/issues). For a
new model, include a redacted status response and explain which physical state
or setting each observed value represents. Do not enable write controls for an
unverified model.

## License and attribution

Distributed under the [MIT License](LICENSE.md). Copyright in upstream
contributions remains with their respective authors; the project lineage is
documented above.

Special thanks to [Oliver Falvai](https://github.com/ofalvai) for the original
integration and to [Fabio Mauro](https://github.com/bigmoby) for the upstream
fork and its continued development.
