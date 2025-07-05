import boto3
from time import sleep
import json
import logging
import sys

from .list_users import (
    list_all_cognito_users,
    cognito_user_to_canonical,
    canonical_to_cognito_user,
    cognito_client,
    user_pool_id,
)


def cognito_list_groups():
    response = cognito_client.list_groups(
        UserPoolId=user_pool_id,
    )

    groups = response.get("Groups", [])
    while "NextToken" in response:
        response = cognito_client.list_groups(
            UserPoolId=user_pool_id,
            NextToken=response["NextToken"],
        )
        groups.extend(response.get("Groups", []))
        sleep(0.1)

    return groups

def cognito_list_users_in_group_canonical(group_name):
    users = cognito_list_users_in_group(group_name)
    return [cognito_user_to_canonical(user) for user in users]

def cognito_list_users_in_group(group_name):
    response = cognito_client.list_users_in_group(
        UserPoolId=user_pool_id,
        GroupName=group_name,
    )

    users = response.get("Users", [])
    while "NextToken" in response:
        response = cognito_client.list_users_in_group(
            UserPoolId=user_pool_id,
            GroupName=group_name,
            PaginationToken=response["NextToken"],
        )
        users.extend(response.get("Users", []))
        sleep(0.1)

    return users



