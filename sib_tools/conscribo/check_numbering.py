from . import auth
from .relations import list_relations_persoon, update_relation
from .groups import get_group_members
from . import groups
from time import sleep
import logging
import sys

def is_external_number(conscribo_id):
    """
    Check if the conscribo_id is an external number.
    External numbers are >= 2000.
    """
    return int(conscribo_id) >= 2000 or conscribo_id == "666"


def check_relation_number_correct(relation):
    conscribo_id = relation["conscribo_id"]

    donateurs = groups.donateurs
    externen = groups.externen
    overige_externen_voor_incassos = groups.overige_externen_voor_incassos

    expected_member = int(relation["conscribo_id"]) < 2000
    external_groups = []
    if conscribo_id in externen:
        external_groups.append("externen")
    if conscribo_id in overige_externen_voor_incassos:
        external_groups.append("overige_externen_voor_incassos")
    if conscribo_id in donateurs:
        external_groups.append("donateurs")

    is_external = len(external_groups) > 0
    is_member = not is_external

    if expected_member == is_member:
        return True

    selector = relation["other"]["selector"]

    if is_member:
        logging.warning(f"\x1b[33mProblem found: \x1b[0m")
        logging.warning(f"  Member \x1b[93m'{selector}'\x1b[0m has inconsistent conscribo_id: {conscribo_id}. ")
        logging.warning("  Explanation: Member ids should be < 2000.")
        logging.warning("  The relation is presumed to be a member, since it is not in any of the external groups: ")
        logging.warning(f"    - Externen, Overige externen voor incassos, Donateurs")
        logging.warning("")
        return False

    if is_external:
        logging.warning(f"\x1b[33mProblem found: \x1b[0m")
        logging.warning(f"  External \x1b[93m'{selector}'\x1b[0m has inconsistent conscribo_id: {conscribo_id}.")
        logging.warning("  Explanation: External ids should be >= 2000.")
        logging.warning("  The relation is presumed to be an external, since it is in these external groups: ")
        logging.warning(f"    - {', '.join(external_groups)}")
        logging.warning("")
        return False
    
    return False


def check_numbering():
    logging.basicConfig(
        filename="conscribo_check_numbering.log",
        level=logging.DEBUG,
        format="[%(asctime)s] %(levelname)s: %(message)s",
    )
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    logging.info("\x1b[94mPreparing...\x1b[0m")

    auth.do_auth()

    relations = list_relations_persoon()
    logging.info(f"Fetched {len(relations)} relations from Conscribo.")
    logging.info("")

    logging.info("\x1b[94mPreparation done.\x1b[0m\n")

    correct = 0
    wrong = 0

    for relation in relations:
        try:
            if check_relation_number_correct(relation):
                correct += 1
            else:
                wrong += 1
        except Exception as e:
            wrong += 1
            logging.error(f"Error processing relation {relation['conscribo_id']}: {e}")
        

    logging.info("")
    logging.info(f"Processed {len(relations)} relations: {correct} correct, {wrong} wrong.")
    logging.info("")
