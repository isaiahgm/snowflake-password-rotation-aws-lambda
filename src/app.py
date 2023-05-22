import logging
import os
import json

import boto3

import bi_snowflake_connector
from snowflake.connector.errors import ProgrammingError

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger('snowflake').setLevel(logging.WARNING)
logging.getLogger('boto3').setLevel(logging.WARNING)

def handler(event, context):
    """Secrets Manager Rotation Template

    This is a template for creating an AWS Secrets Manager rotation lambda

    Args:
        event (dict): Lambda dictionary of event parameters. These keys must include the following:
            - SecretId: The secret ARN or identifier
            - ClientRequestToken: The ClientRequestToken of the secret version
            - Step: The rotation step (one of createSecret, setSecret, testSecret, or finishSecret)

        context (LambdaContext): The Lambda runtime information

    Raises:
        ResourceNotFoundException: If the secret with the specified arn and stage does not exist

        ValueError: If the secret is not properly configured for rotation

        KeyError: If the event parameters do not contain the expected keys

    """
    arn = event['SecretId']
    token = event['ClientRequestToken']
    step = event['Step']
    logging.info(f'Begin password rotation step {step} for {arn} with token {token}...')

    # Setup the client
    logging.info(f'Connect to secretsmanager...')
    service_client = boto3.client('secretsmanager')

    # Make sure the version is staged correctly
    metadata = service_client.describe_secret(SecretId=arn)
    if not metadata['RotationEnabled']:
        logger.error("Secret %s is not enabled for rotation" % arn)
        raise ValueError("Secret %s is not enabled for rotation" % arn)
    versions = metadata['VersionIdsToStages']
    if token not in versions:
        logger.error("Secret version %s has no stage for rotation of secret %s." % (token, arn))
        raise ValueError("Secret version %s has no stage for rotation of secret %s." % (token, arn))
    if "AWSCURRENT" in versions[token]:
        logger.info("Secret version %s already set as AWSCURRENT for secret %s." % (token, arn))
        return
    elif "AWSPENDING" not in versions[token]:
        logger.error("Secret version %s not set as AWSPENDING for rotation of secret %s." % (token, arn))
        raise ValueError("Secret version %s not set as AWSPENDING for rotation of secret %s." % (token, arn))

    if step == "createSecret":
        create_secret(service_client, arn, token)

    elif step == "setSecret":
        set_secret(service_client, arn, token)

    elif step == "testSecret":
        test_secret(service_client, arn, token)

    elif step == "finishSecret":
        finish_secret(service_client, arn, token)

    else:
        raise ValueError("Invalid step parameter")


def create_secret(service_client, arn, token):
    """Create the secret

    This method first checks for the existence of a secret for the passed in token. If one does not exist, it will
    generate a new secret and put it with the passed in token.

    Args:
        service_client (client): The secrets manager service client

        arn (string): The secret ARN or other identifier

        token (string): The ClientRequestToken associated with the secret version

    Raises:
        ResourceNotFoundException: If the secret with the specified arn and stage does not exist

    """
    logging.info('createSecret: Started...')
    logging.info(f'Get AWSCURRENT secret value of {arn}...')
    current_secret = service_client.get_secret_value(SecretId=arn, VersionStage="AWSCURRENT")

    try:
        service_client.get_secret_value(SecretId=arn, VersionId=token, VersionStage="AWSPENDING")
        logging.warning('AWSPENDING version already exists, skip generating a new secret...')
        logger.info("createSecret: Successfully retrieved secret for %s." % arn)
    except service_client.exceptions.ResourceNotFoundException:
        logging.info('Generate new secret...')
        exclude_characters = os.environ['EXCLUDE_CHARACTERS'] if 'EXCLUDE_CHARACTERS' in os.environ else '/@"\'\\`'
        passwd = service_client.get_random_password(ExcludeCharacters=exclude_characters)

        current_secret_str = json.loads(current_secret['SecretString'])
        username = current_secret_str['username']

        secret_str = json.dumps({"username": username, "password": passwd['RandomPassword']})

        logging.info('Put new secret as AWSPENDING...')
        service_client.put_secret_value(SecretId=arn, ClientRequestToken=token, SecretString=secret_str,
                                        VersionStages=['AWSPENDING'])
        logger.info("createSecret: Successfully put secret for ARN %s and version %s." % (arn, token))


def set_secret(service_client, arn, token):
    """Set the secret

    This method should set the AWSPENDING secret in the service that the secret belongs to. For example, if the secret
    is a database credential, this method should take the value of the AWSPENDING secret and set the user's password to
    this value in the database.

    Args:
        service_client (client): The secrets manager service client

        arn (string): The secret ARN or other identifier

        token (string): The ClientRequestToken associated with the secret version

    """
    logging.info('setSecret: Started...')
    logging.info(f'Get AWSPENDING version of secret {arn}...')
    secret = service_client.get_secret_value(SecretId=arn, VersionId=token, VersionStage="AWSPENDING")
    secret_str = json.loads(secret['SecretString'])

    username = secret_str['username']
    password = secret_str['password']

    try:
        with bi_snowflake_connector.connect() as snow_con:
            with snow_con.cursor() as cursor:
                logging.info(f'Set new password for {username}...')
                cursor.execute("USE ROLE SECURITYADMIN;")
                cursor.execute(f"ALTER USER {username} SET PASSWORD='{password}';")
    except ProgrammingError as e:
        if e.errno == 3002:
            logging.warning(f'PRIOR USE error detected, continuing without setting password...')
        else:
            raise e

    logger.info(f"setSecret: Successfully set secret for {arn} and version {token} in Snowflake.")


def test_secret(service_client, arn, token):
    """Test the secret

    This method should validate that the AWSPENDING secret works in the service that the secret belongs to. For example,
    if the secret is a database credential, this method should validate that the user can login with the password in
    AWSPENDING and that the user has all of the expected permissions against the database.

    Args:
        service_client (client): The secrets manager service client

        arn (string): The secret ARN or other identifier

        token (string): The ClientRequestToken associated with the secret version

    """
    logging.info('testSecret: Started...')
    logging.info('Get AWSPENDING secret version...')
    secret = service_client.get_secret_value(SecretId=arn, VersionId=token, VersionStage="AWSPENDING")
    secret_str = json.loads(secret['SecretString'])

    username = secret_str['username']
    password = secret_str['password']

    logging.info('Test connecting to Snowflake...')
    snow_con = bi_snowflake_connector.connect(username=username, password=password)
    snow_con.close()

    logger.info(f"testSecret: Successfully tested secret for {arn} and version {token} in Snowflake.")


def finish_secret(service_client, arn, token):
    """Finish the secret

    This method finalizes the rotation process by marking the secret version passed in as the AWSCURRENT secret.

    Args:
        service_client (client): The secrets manager service client

        arn (string): The secret ARN or other identifier

        token (string): The ClientRequestToken associated with the secret version

    Raises:
        ResourceNotFoundException: If the secret with the specified arn does not exist

    """
    # First describe the secret to get the current version
    logging.info('finishSecret: Started...')

    metadata = service_client.describe_secret(SecretId=arn)
    current_version = None
    pending_versions = []
    for version in metadata["VersionIdsToStages"]:
        if "AWSCURRENT" in metadata["VersionIdsToStages"][version]:
            current_version = version
        if "AWSPENDING" in metadata["VersionIdsToStages"][version]:
            pending_versions.append(version)

    if current_version == token:
        logger.info("finishSecret: Version %s already marked as AWSCURRENT for %s" % (version, arn))
    else:
        logging.info(f'Set version {token} as AWSCURRENT...')
        service_client.update_secret_version_stage(SecretId=arn, VersionStage="AWSCURRENT", MoveToVersionId=token,
                                                   RemoveFromVersionId=current_version)
        logger.info("finishSecret: Successfully set AWSCURRENT stage to version %s for secret %s." % (token, arn))

    for version in pending_versions:
        logging.info(f'Cleanup: Remove AWSPENDING tag from {version}...')
        service_client.update_secret_version_stage(SecretId=arn, VersionStage="AWSPENDING", RemoveFromVersionId=token)
