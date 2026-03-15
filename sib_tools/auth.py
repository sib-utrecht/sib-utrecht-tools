import os
import importlib
import keyring
import logging
import sys
from typing import Any, Callable, Protocol, TypedDict, NotRequired, cast


class _SelectFn(Protocol):
    def __call__(
        self,
        options: list[Any],
        *,
        cursor: str,
        cursor_style: str,
        return_index: bool,
    ) -> int | None: ...


try:
    select = cast(_SelectFn | None, importlib.import_module("beaupy").select)
except Exception:
    select = None


ActionFn = Callable[[], Any]
CheckAvailableFn = Callable[[], Any]


class ServiceDef(TypedDict):
    name: str
    key: str
    signin: ActionFn
    show: ActionFn
    check_available: CheckAvailableFn
    signout: ActionFn
    rotate: NotRequired[ActionFn]


def configure_keyring() -> None:
    if "KEYRING_CRYPTFILE_PASSWORD" in os.environ:
        cryptfile_module = importlib.import_module("keyrings.cryptfile.cryptfile")
        CryptFileKeyring = cast(type[Any], getattr(cryptfile_module, "CryptFileKeyring"))

        kr = CryptFileKeyring()
        kr.keyring_key = os.environ["KEYRING_CRYPTFILE_PASSWORD"]
        keyring.set_keyring(kr)


def check_available_auth(logger: logging.Logger | None = None, non_interactive: bool = False, signin_action: str | None = None) -> None:
    from sib_tools.aws import auth as aws_auth
    from sib_tools.conscribo import auth as conscribo_auth
    from sib_tools.laposta import auth as laposta_auth
    from sib_tools.grist import auth as grist_auth
    from sib_tools.google import auth as google_auth
    from sib_tools.sib_app import auth as sib_app_auth

    if not logger:
        logger = logging.getLogger("sib_tools_check")
        stream_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(stream_handler)
        logger.setLevel(logging.INFO)

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    subactions = ["signin", "rotate", "show", "signout"]

    services: list[ServiceDef] = [
        {
            "name": "AWS (used for Cognito and e-mails)",
            "key": "aws",
            "signin": aws_auth.prompt_credentials,
            "rotate": aws_auth.rotate_aws_credentials,
            "show": aws_auth.show,
            "check_available": aws_auth.check_available,
            "signout": aws_auth.signout,
        },
        {
            "name": "Conscribo",
            "key": "conscribo",
            "signin": conscribo_auth.prompt_credentials,
            "show": conscribo_auth.show,
            "check_available": conscribo_auth.check_available,
            "signout": conscribo_auth.signout,
        },
        {
            "name": "Laposta",
            "key": "laposta",
            "signin": laposta_auth.prompt_credentials,
            "show": laposta_auth.show,
            "check_available": laposta_auth.check_available,
            "signout": laposta_auth.signout,
        },
        {
            "name": "SIB App",
            "key": "sib_app",
            "signin": sib_app_auth.prompt_credentials,
            "show": sib_app_auth.show,
            "check_available": sib_app_auth.check_available,
            "signout": sib_app_auth.signout,
        },
        {
            "name": "Grist",
            "key": "grist",
            "signin": grist_auth.prompt_credentials,
            "show": grist_auth.show,
            "check_available": grist_auth.check_available,
            "signout": grist_auth.signout,
        },
        {
            "name": "Google",
            "key": "google",
            "signin": google_auth.prompt_credentials,
            "show": google_auth.show,
            "check_available": google_auth.check_available,
            "signout": google_auth.signout,
        },
    ]

    def msg(s: str) -> None:
        if non_interactive:
            logger.info(s)
        else:
            print(s)

    msg(f"\n{BOLD}{CYAN}Authentication status for services:{RESET}")
    missing: list[ServiceDef] = []
    for svc in services:
        try:
            cred = svc["check_available"]()
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

    available_subactions: list[str] = []

    if not signin_action:
        msg(
            f"\n{BOLD}Select a service to sign in, rotate, or sign out (or choose 'Cancel' to skip):{RESET}"
        )
        selection_options: list[tuple[ServiceDef | None, list[str], str]] = [
            (None, [], f"{YELLOW}Cancel{RESET}")
        ]
        for svc in services:
            available_subactions = [a for a in subactions if a in svc]
            if not available_subactions:
                continue

            selection_options.append(
                (svc, available_subactions, f"{svc['name']} ({' | '.join(available_subactions)})")
            )

        option_descriptions = [desc for _, _, desc in selection_options]

        assert select is not None
        service_index = select(
            cast(list[Any], option_descriptions), cursor="→", cursor_style="blue", return_index=True
        )

        service: ServiceDef | None = None
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
        assert select is not None
        idx = select(
            cast(list[Any], option_descriptions), cursor="→", cursor_style="blue", return_index=True
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
    action_map: dict[str, ServiceDef] = {svc["key"]: svc for svc in services}
    try:
        service_key, action = signin_action.split(":", 1)
        selected_service = action_map.get(service_key)
        if not selected_service:
            msg(f"{YELLOW}Unknown service '{service_key}'.{RESET}")
            return
        trigger = cast(ActionFn | None, selected_service.get(action))

        if not trigger:
            msg(f"{YELLOW}Action '{action}' not supported for {selected_service['name']}.{RESET}")
            return

        trigger()

        msg(f"{YELLOW}Executed action '{signin_action}'.{RESET}")

    except Exception as e:
        msg(f"{YELLOW}Error: {e}{RESET}")
