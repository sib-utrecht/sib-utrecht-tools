# SIB-Utrecht Tools (sib_tools)

Tools for member administration for SIB-Utrecht. This repository provides a Python script for synchronising data with external services, listing information, checking data integrity and handling incoming email.

For example, if a person registers via the website to become a member, the
following happens:

1. An e-mail with all the details of the registration is also sent to 'register' +
@ 'automations.sib-utrecht.nl', at AWS SES. It triggers an SNS notification,
which invokes an HTTPS endpoint, which is proxied to `sib_tools/listen_sns_for_email.py`. 
2. The script verifies the e-mail, extracts fields, and adds the person to our
   member administration at Conscribo.
3. A daily timer invokes `python -m sib_tools sync all --mail-output`. This will
   add the person to other services:
    1. __AWS Cognito__, which we use as login system.
    2. __Laposta__, which we use for the newsletter, and sending birthday 
      congratulations.
    3. __Google Contacts__, which makes it easy to e-mail members, look up other
      information, and for memberXXX@anon.sib-utrecht.nl email addresses.
    4. __Google Groups__, to assemble mailing lists members@sib-utrecht.nl and
      alumni@sib-utrecht.nl. These can be used to easily mail our members and alumni.
    5. __Activity signup system__, to let it know how to display a signup for
      a given user id.


## Where is this running?

The daily synchronisation call runs on SIB's server instance at OVH Cloud. You
can enter it by `shh sib-tools@edit.sib-utrecht.nl`. The password is known to
the board of SIB-Utrecht.

After logging in, you can type `sib-tools --help` and press enter. This will
show you the commands you can invoke.

> [!WARNING]
> The login credentials should only be known by the board, since anyone logging
> in could manipulate the program can read and write to Conscribo, or any of the 
> external services.

## How do I make changes?

To make live changes, test them, or just to deploy changes committed to `main`, log in on the server. The easiest way is to log in via VS Code, with the `Remote - SSH` extension installed. Then add a remote, connect to it, and open `~/sib-utrecht-tools`. Use the Git extension to pull and push to the repository. Don't do it via the command line, because it will try to use Git credentials on the server itself, which are absent.

Changes you make will be immediate, both for running it yourself, and for the daily invocation of `sib-tools sync all --mail-output`. However, for the listener of incoming e-mail, you must also run `./restart.sh`, before the changes take effect.


## Quick start on local computer

1) Create and activate a virtual environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2) Install dependencies

```bash
pip install -r sib_tools/requirements.txt
```

3) Run the CLI

- Using Python module invocation (works from a clone):
  ```bash
  python -m sib_tools --help
  ```
- If you use this project on the server, use:
  ```bash
  sib-tools --help
  ```

## CLI overview

The CLI is implemented with Python's argparse. Top-level commands are registered in `sib_tools/__main__.py` and each command has its own module. General usage:

```bash
python -m sib_tools <command> [subcommand] [options]
```

On the server, use the `./sib-tools.sh` or `sib-tools` entrypoint instead:
```bash
sib-tools <command> [subcommand] [options]
```
This will ensure the credentials are loaded.


Available commands:

- sync — Synchronize members to other services (e.g., Laposta, website accounts)
  - Show options: `python -m sib_tools sync --help`
- list — List information
  - Show options: `python -m sib_tools list --help`
- api — Issue a raw API command
  - Example: `python -m sib_tools api conscribo get /relations/groups/`
- check — Check data consistency and integrity
  - Show options: `python -m sib_tools check --help`
- email — Email-related subcommands (parsers are registered under this group)
  - Show options: `python -m sib_tools email --help`
- serve — Run server endpoints (e.g., for AWS SNS webhooks)
  - Show options: `python -m sib_tools serve --help`
- auth — Cognito user management actions
  - Show options: `python -m sib_tools auth --help`

Tip: You can always append `--help` after any command/subcommand to see detailed usage and defaults.

## Project structure

High-level layout of the `sib_tools` package:

- `sib_tools/__main__.py` — CLI entry point. Wires subcommands.
- `sib_tools/command_exception.py` — Shared exception type for CLI commands.
- `sib_tools/auth.py` — Keyring setup (`configure_keyring`) and auth helpers. Initialized at startup.
- Command modules (each registers its own parser):
  - `sib_tools/sync_command.py` — Implements `sync`
  - `sib_tools/list_command.py` — Implements `list`
  - `sib_tools/api_command.py` — Implements `api`
  - `sib_tools/check_command.py` — Implements `check`
  - `sib_tools/serve_command.py` — Implements `serve`
  - `sib_tools/auth_command.py` — Implements `auth`
  - `sib_tools/email/` — Email command group and helpers
- Service/client integrations and helpers:
  - `sib_tools/sync/` — Sync logic and targets
  - `sib_tools/conscribo/` — Conscribo API integration
  - `sib_tools/cognito/` — AWS Cognito utilities
  - `sib_tools/laposta/` — Laposta integration
  - `sib_tools/google/`, `sib_tools/grist/`, `sib_tools/aws/`, `sib_tools/canonical/`, `sib_tools/sib_app/` — Other integrations and shared code
- Utilities:
  - `sib_tools/utils.py` — Common utility functions
  - `sib_tools/listen_sns_for_email.py` — SNS listener utilities for incoming email

Repository root contains helper scripts and logs used in deployments/operations, for example:

- `restart.sh`, `sib-tools.sh`, `launch-with-aws.sh` — Operational scripts
- `sib_tools_incoming_email.log`, `sns_incoming.log`, `conscribo_api.log` — Runtime logs

## Credentials and keyring

The CLI initializes the Python `keyring` backend via `configure_keyring()` at startup. Credentials/secrets used by commands are retrieved from the system keyring where possible. Ensure your environment has a functional keyring backend (on headless Linux, like on the server, or when a daily systemd trigger is running it, we must fallback to an encrypted file-based keyring, where the encryption key is provided by an environment variable. See `sib-tools.sh`.)

## Examples

- List available groups from API:
  ```bash
  python -m sib_tools api "GET /relations/groups/"
  ```
- Inspect sync options:
  ```bash
  python -m sib_tools sync --help
  ```
- Run data checks:
  ```bash
  python -m sib_tools check --help
  ```
- Manage Cognito users:
  ```bash
  python -m sib_tools auth --help
  ```
- Serve webhook endpoints (e.g. SNS):
  ```bash
  python -m sib_tools serve --help
  ```

## VS Code tasks (optional)

If you are using VS Code in this workspace, some helpful tasks may be available:

- Restart SIB Tools — `./restart.sh`
- Listen for email log — `journalctl -fu sib-tools-listen-email`
- Tail Incoming Email Log — `tail -f sib_tools_incoming_email.log`
- Tail All Incoming Logs — `tail -f sib_tools_incoming_email.log sib_tools_check.log sns_incoming.log conscribo_api.log`

Open the Command Palettec (Ctrl+Shift+P) → "Run Task" to discover and run these tasks.

## Troubleshooting

- Use `--help` frequently to understand available flags and defaults.
- Ensure dependencies are installed from `sib_tools/requirements.txt` in an active virtual environment.
- Verify your keyring backend is working if commands require credentials.
- For operational issues, consult the logs at the repository root and/or the VS Code tasks above.
- If you're not from the IT committee, and are having trouble, ask the committee.
- If you're the IT committee, and you're having trouble, contact the original
  author of this package: [Vincent Kuhlmann](https://github.com/vkuhlmann/)
