"""
Sync canonical members to a Conscribo group/list.
This sync allows you to set the members of a specific Conscribo group
based on a list of canonical members.
"""

import json
import logging
import sys
from typing import List, Dict, Any

from ..conscribo.groups import set_group_members
from ..conscribo.relations import list_relations_active_members, list_relations_active_alumni
from ..canonical import canonical_key


logging.basicConfig(
    filename="conscribo_list_sync.log", 
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
)

# Only print INFO and above to stdout
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(console_handler)


def sync_conscribo_to_conscribo_list(
    group_id: int, 
    canonical_members: List[Dict[str, Any]], 
    dry_run: bool = True,
    logger: logging.Logger | None = None,
):
    """
    Sync canonical members to a specific Conscribo group.
    
    Args:
        group_id: The ID of the Conscribo group to sync to
        canonical_members: List of canonical member dictionaries
        dry_run: If True, only show what would be changed without making actual changes
    """
    logger = logger or logging.getLogger(__name__)

    logger.info(f"Syncing {len(canonical_members)} canonical members to Conscribo group {group_id}")
    
    if dry_run:
        logger.info("DRY RUN MODE - No actual changes will be made")
    
    # Use the set_group_members method from groups.py
    set_group_members(group_id, canonical_members, dry_run=dry_run)
    
    logger.info("Sync completed")


def sync_active_members_to_group(group_id: int, dry_run: bool = True, logger: logging.Logger | None = None):
    """
    Convenience function to sync all active members to a group.
    """
    logger = logger or logging.getLogger(__name__)
    active_members = list_relations_active_members()
    sync_conscribo_to_conscribo_list(group_id, active_members, dry_run, logger=logger)


def sync_active_alumni_to_group(group_id: int, dry_run: bool = True, logger: logging.Logger | None = None):
    """
    Convenience function to sync all active alumni to a group.
    """
    logger = logger or logging.getLogger(__name__)
    active_alumni = list_relations_active_alumni()
    sync_conscribo_to_conscribo_list(group_id, active_alumni, dry_run, logger=logger)
