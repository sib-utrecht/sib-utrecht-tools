import logging

from ..cognito.list_users import list_all_cognito_users, cognito_user_to_canonical, list_cognito_users_canonical
from ..sib_app.wp_old_users import fetch_users_by_wp_user_id, create_user, delete_user
from ..utils import print_header
from typing import Any
from time import sleep, time
import json
from ..cognito.client import (
    cognito_client,
    user_pool_id,
)

def sync_cognito_to_wp(dry_run: bool = True, logger: logging.Logger | None = None) -> int:
    """
    Print out the list of WordPress user IDs present in Cognito and the ones in WordPress (SIB App).
    Additionally:
      - For IDs present only in Cognito, create WordPress users.
      - For IDs present only in WordPress, delete WordPress users if wordpress_user_id >= 1000.
    Returns the number of changes (creates + deletes).
    """
    logger = logger or logging.getLogger(__name__)

    print_header(
        "Syncing Cognito to WordPress users for SIB app...",
        logger,
    )

    if dry_run:
        logger.info(f"Dry run: {dry_run}")

    # Gather WordPress (SIB App) users keyed by wordpress_user_id
    wp_users_by_id = fetch_users_by_wp_user_id(min_wp_user_id=0)
    wp_wp_ids = sorted(wp_users_by_id.keys())

    # Gather Cognito users and extract their wp_user_id (if present)
    cognito_users = list_cognito_users_canonical()
    full_cognito_count = len(cognito_users)

    cognito_users = [
        a for a in cognito_users
        if (a.get("conscribo_id") or "ignore") != "ignore"
    ]
    logger.info(f"Skipping {full_cognito_count - len(cognito_users)} Cognito users without conscribo_id")

    cognito_only = []
    matched : list[tuple[dict[str, Any], dict[str, Any]]] = []

    for user in cognito_users:
        wordpress_user = wp_users_by_id.get(user.get("wp_user_id"))
        if not wordpress_user:
            cognito_only.append(user)
            continue
        
        matched.append((user, wordpress_user))

    # Map for quick lookup by wp_user_id
    cognito_by_wp_id: dict[int, dict] = {
        int(a["wp_user_id"]): a
        for a in cognito_users
        if isinstance(a.get("wp_user_id"), int)
    }

    cognito_wp_ids_set: set[int] = set(cognito_by_wp_id.keys())
    cognito_wp_ids = sorted(cognito_wp_ids_set)

    logger.info(f"Cognito WordPress user IDs ({len(cognito_wp_ids)}):")
    logger.info(
        ", ".join(map(str, cognito_wp_ids)) if cognito_wp_ids else "(none)"
    )
    logger.info("")

    logger.info(f"WordPress user IDs ({len(wp_wp_ids)}):")
    logger.info(", ".join(map(str, wp_wp_ids)) if wp_wp_ids else "(none)")
    logger.info("")

    # Show simple difference for convenience
    wp_only = sorted(set(wp_wp_ids) - set(cognito_wp_ids))

    logger.info(
        f"In WordPress only ({len(wp_only)}): {', '.join(map(str, wp_only))}"
    )
    logger.info(
        f"In Cognito only ({len(cognito_only)}): Conscribo Ids: {', '.join(a.get("conscribo_id") for a in cognito_only)}"
    )

    change_count = 0

    # Create WP users for Cognito-only IDs
    for cognito_user in cognito_only:
        canonical = cognito_user
        conscribo_id = canonical.get("conscribo_id")
        # if conscribo_id != "329":
        #     continue

        basics = (
            canonical.get("first_name", ""),
            canonical.get("last_name", ""),
            canonical.get("email", ""),
        )
        logger.info(f"CREATE WordPress user for {conscribo_id} {json.dumps(basics)}")
        change_count += 1
        if dry_run:
            continue
        try:
            # Ensure the canonical has the intended wp_user_id
            result = create_user(canonical)
            wp_user_id = result["wp_user_id"]
            entity_id = result["entity_id"]

            # Update Cognito user
            start_time = time()
            cognito_client.admin_update_user_attributes(
                UserPoolId=user_pool_id,
                Username=canonical["cognito_sub"],
                UserAttributes=[
                    {
                        "Name": "custom:wp-userid",
                        "Value": str(wp_user_id),
                    },
                    {
                        "Name": "custom:entity-id",
                        "Value": entity_id
                    }
                ],
            )
            end_time = time()
            elapsed_time = end_time - start_time

            sleep(0.05)
        except Exception as e:
            logger.error(f"Failed to create WordPress user for {conscribo_id}: {e}")

    # Delete WP users for WordPress-only IDs with id >= 1000
    for wp_id in wp_only:
        if wp_id < 1000:
            # logger.info(f"SKIP delete WordPress user {wp_id} (< 1000)")
            continue

        wp_user = wp_users_by_id.get(wp_id)
        if not wp_user:
            logger.warning(f"No WordPress user found for wp_user_id={wp_id}, skipping delete")
            continue

        conscribo_id = wp_user.get("details", {}).get("conscribo_id")
        logger.info(f"WordPress user {wp_id} is linked to conscribo_id {conscribo_id}")

        entity_name = (wp_user or {}).get("entity_name") or f"user-2025-{wp_id}"
        logger.info(f"DELETE WordPress user {wp_id} ({entity_name})")
        change_count += 1
        if dry_run:
            continue
        try:
            delete_user(entity_name)
        except Exception as e:
            logger.error(f"Failed to delete WordPress user {wp_id} ({entity_name}): {e}")

    return change_count
