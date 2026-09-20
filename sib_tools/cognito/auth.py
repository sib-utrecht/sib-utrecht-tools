from ..aws.auth import get_aws_credentials

def get_cognito_credentials() -> tuple[str | None, str | None, str | None]:
    return get_aws_credentials()
