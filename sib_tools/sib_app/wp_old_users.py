from .auth import sib_app_get, sib_app_post, sib_app_delete
from datetime import datetime

def fetch_users(min_wp_user_id):
    response = sib_app_get("/v2/users", parameters={"min_wp_user_id": min_wp_user_id})
    return response["data"]["users"]

def fetch_users_by_wp_user_id(min_wp_user_id):
    res = fetch_users(min_wp_user_id)
    return {u['wordpress_user_id']: u for u in res}

def create_user(canonical):
    conscribo_id = canonical.get("conscribo_id")
    first_name = canonical.get("first_name")
    last_name = canonical.get("last_name")
    email = canonical.get("email")

    wp_user_id = canonical.get("wp_user_id")

    if not wp_user_id:
        wp_user_id = int(conscribo_id) + 1000

    entity_name = f"user-2025-{wp_user_id}"

    sib_app_post("/v2/users", body={
        "entity_name": entity_name,
        "wordpress_user_id": wp_user_id,
        "long_name": f"{first_name} {last_name}",
        "short_name": first_name,
        "details": {
            "created": datetime.now().isoformat().replace("T", " ")[:19],
            "conscribo_id": conscribo_id,
            "email": email,
            "legal_name": {
                "first_name": first_name,
                "last_name": last_name
            }

        }
    })

    return {
        "wp_user_id": wp_user_id,
        "entity_id": entity_name
    }

def delete_user(entity_name):
    if len(entity_name) == 0:
        raise ValueError("Empty entity_name not allowed for delete_user()")

    print(f"Deleting user {entity_name}")
    sib_app_delete(f"/v2/users/{entity_name}")
