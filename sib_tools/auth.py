import os
import keyring
import logging
import sys


def configure_keyring():
    if "KEYRING_CRYPTFILE_PASSWORD" in os.environ:
        from keyrings.cryptfile.cryptfile import CryptFileKeyring

        kr = CryptFileKeyring()
        kr.keyring_key = os.environ["KEYRING_CRYPTFILE_PASSWORD"]
        keyring.set_keyring(kr)


def check_available_auth(logger=None, non_interactive=False, signin_action=None):
    from sib_tools.aws import auth as aws_auth
    from sib_tools.conscribo import auth as conscribo_auth
    from sib_tools.laposta import auth as laposta_auth
    from sib_tools.grist import auth as grist_auth
    from sib_tools.google import auth as google_auth

    if not logger:
        logger = logging.getLogger("sib_tools_check")
        stream_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(stream_handler)
        logger.setLevel(logging.INFO)

    if not non_interactive:
        from beaupy import select

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    subactions = ["signin", "rotate", "signout"]

    services = [
        {
            "name": "AWS (used for Cognito and e-mails)",
            "key": "aws",
            "signin": aws_auth.prompt_credentials,
            "rotate": aws_auth.rotate_aws_credentials,
            "check-available": aws_auth.check_available,
            "signout": aws_auth.signout,
        },
        {
            "name": "Conscribo",
            "key": "conscribo",
            "signin": conscribo_auth.prompt_credentials,
            "check-available": conscribo_auth.check_available,
            "signout": conscribo_auth.signout,
        },
        {
            "name": "Laposta",
            "key": "laposta",
            "signin": laposta_auth.prompt_credentials,
            "check-available": laposta_auth.check_available,
            "signout": laposta_auth.signout,
        },
        {
            "name": "Grist",
            "key": "grist",
            "signin": grist_auth.prompt_credentials,
            "check-available": grist_auth.check_available,
            "signout": grist_auth.signout,
        },
        {
            "name": "Google",
            "key": "google",
            "signin": lambda: google_auth.prompt_and_store_in_keyring(
                "GOOGLE_ADMIN_EMAIL", "Enter your Google Workspace admin email: "
            ),
            "check-available": google_auth.check_available,
            "signout": google_auth.signout,
        },
    ]
    msg = lambda s: (logger.info(s) if non_interactive else print(s))
    msg(f"\n{BOLD}{CYAN}Authentication status for services:{RESET}")
    missing = []
    for svc in services:
        try:
            cred = svc["check-available"]()
            if cred:
                msg(f"{GREEN}[OK]{RESET} {svc['name']} credentials present.")
            else:
                msg(f"{RED}[MISSING]{RESET} {svc['name']} credentials not found.")
                missing.append(svc)
        except Exception as e:
            msg(f"{YELLOW}[ERROR]{RESET} {svc['name']}: {e}")
            missing.append(svc)

    if not missing:
        msg(f"{GREEN}All credentials are present!{RESET}")
    msg("")

    if non_interactive and not signin_action:
        msg(f"{YELLOW}Non-interactive mode: not prompting for sign-in.{RESET}")
        return

    if not signin_action:
        msg(
            f"\n{BOLD}Select a service to sign in, rotate, or sign out (or choose 'Cancel' to skip):{RESET}"
        )
        selection_options = [(None, [], f"{YELLOW}Cancel{RESET}")]
        for svc in services:
            available_subactions = list(filter(lambda x: x in svc, subactions))
            if not available_subactions:
                continue

            selection_options.append(
                (svc, available_subactions, f"{svc['name']} ({' | '.join(available_subactions)})")
            )

        option_descriptions = [desc for _, _, desc in selection_options]

        service_index = idx = select(
            option_descriptions, cursor="→", cursor_style="blue", return_index=True
        )

        service = None
        if service_index is not None:
            service, available_subactions, _ = selection_options[service_index]

        if service is None:
            msg(f"{YELLOW}No service selected.{RESET}")
            msg(f"\n{BOLD}Done.{RESET}")
            return
        
        msg(f"\n{BOLD}Selected service: {service['name']}{RESET}")
        # Select subaction
        subaction_options = [
            (None, f"{YELLOW}Cancel{RESET}")
        ] + [
            (f"{service['key']}:{action}", f"{action}")
            for action in available_subactions
        ]

        option_descriptions = [desc for _, desc in subaction_options]
        idx = select(
            option_descriptions, cursor="→", cursor_style="blue", return_index=True
        )

        signin_action = None
        if idx is not None:
            signin_action, _ = subaction_options[idx]

        if signin_action is None:
            msg(f"{YELLOW}No action selected.{RESET}")
            msg(f"\n{BOLD}Done.{RESET}")
            return
        
    msg(f"{YELLOW}Executing action '{signin_action}'.{RESET}")
        
    # Now handle the action if set
    action_map = {svc["key"]: svc for svc in services}
    try:
        service_key, action = signin_action.split(":", 1)
        svc = action_map.get(service_key)
        if not svc:
            msg(f"{YELLOW}Unknown service '{service_key}'.{RESET}")
            return
        trigger = svc.get(action)

        if not trigger:
            msg(f"{YELLOW}Action '{action}' not supported for {svc['name']}.{RESET}")
            return

        trigger()

        msg(f"{YELLOW}Executed action '{signin_action}'.{RESET}")

    except Exception as e:
        msg(f"{YELLOW}Error: {e}{RESET}")
