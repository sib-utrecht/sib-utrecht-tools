from time import sleep

from .list_users import (
    cognito_user_to_canonical,
    cognito_client as cognito_client,
    user_pool_id as user_pool_id,
)
from typing import Any, cast


def cognito_list_groups() -> list[dict[str, Any]]:
    response = cognito_client.list_groups(
        UserPoolId=user_pool_id,
    )

    groups: list[dict[str, Any]] = cast("list[dict[str, Any]]", list(response.get("Groups", [])))
    while "NextToken" in response:
        response = cognito_client.list_groups(
            UserPoolId=user_pool_id,
            NextToken=response["NextToken"],
        )
        groups.extend(cast("list[dict[str, Any]]", response.get("Groups", [])))
        sleep(0.1)

    return groups

def cognito_list_users_in_group_canonical(group_name: str) -> list[dict[str, Any]]:
    users = cognito_list_users_in_group(group_name)
    return [cognito_user_to_canonical(user) for user in users]

def cognito_list_users_in_group(group_name: str) -> list[dict[str, Any]]:
    response = cognito_client.list_users_in_group(
        UserPoolId=user_pool_id,
        GroupName=group_name,
    )

    users: list[dict[str, Any]] = cast("list[dict[str, Any]]", list(response.get("Users", [])))
    next_token = response.get("NextToken")
    while next_token:
        response = cognito_client.list_users_in_group(
            UserPoolId=user_pool_id,
            GroupName=group_name,
            NextToken=next_token,
        )
        users.extend(cast("list[dict[str, Any]]", response.get("Users", [])))
        next_token = response.get("NextToken")
        sleep(0.1)

    return users



