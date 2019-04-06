from builtins import Exception

import boto3
import json
import os


def get_env_var(name):
    return os.environ[name] if name in os.environ else None


DYNAMO_TABLE_NAME = get_env_var("DYNAMO_TABLE_NAME")
DYNAMO_READ_ROLE = get_env_var("DYNAMO_READ_ROLE")
LAMBDA_FUNCTION_ARN = get_env_var("LAMBDA_FUNCTION_ARN")
DYNAMO_PAGE_LIMIT = int(get_env_var("DYNAMO_PAGE_LIMIT"))


def _create_dynamo_stream_like_object(item):
    return {
        "eventName": "INSERT",
        "eventSource": "aws:dynamodb",
        "dynamodb": {
            "NewImage": item
        },
        "StreamViewType": "BACKFILL_IMAGES"
    }


def _operation_to_perform(items):
    lambda_client = boto3.client('lambda')
    list_of_items = [_create_dynamo_stream_like_object(i) for i in items]

    payload = json.dumps({"Records": list_of_items}).encode('utf-8')
    response = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION_ARN,
        InvocationType='RequestResponse',
        LogType='None',
        Payload=payload
    )
    return 0


def _query_dynamo(ddb_client, context, start_key=None):
    global DYNAMO_TABLE_NAME
    print("reading from table {}".format(DYNAMO_TABLE_NAME))

    paginator = ddb_client.get_paginator('scan')

    if start_key:
        operation_parameters = {
            'ExclusiveStartKey': start_key,
            'Limit': DYNAMO_PAGE_LIMIT,
            'TableName': DYNAMO_TABLE_NAME
        }
    else:
        operation_parameters = {
            'Limit': DYNAMO_PAGE_LIMIT,
            'TableName': DYNAMO_TABLE_NAME
        }
    page_iterator = paginator.paginate(**operation_parameters)
    LastEvaluatedKey = None
    for page in page_iterator:
        if 'LastEvaluatedKey' in page:
            LastEvaluatedKey = page['LastEvaluatedKey']
        else:
            print("on last page")
        print("Time remaining: {} to process {} items".format(context.get_remaining_time_in_millis(), len(page['Items'])))
        _operation_to_perform(page['Items'])
        time_remaining = context.get_remaining_time_in_millis()
        if time_remaining < (60 * 1000) and 'LastEvaluatedKey' in page:
            return LastEvaluatedKey

    return 'DONE'


def _get_ddb_client():
    global DYNAMO_READ_ROLE
    if DYNAMO_READ_ROLE is not None:
        sts = boto3.client('sts')
        role_response = sts.assume_role(
            RoleArn=DYNAMO_READ_ROLE,
            RoleSessionName='my-super-awesome-session'
        )

        ACCESS_KEY_ID = role_response['Credentials']['AccessKeyId']
        SECRET_ACCESS_KEY = role_response['Credentials']['SecretAccessKey']
        SESSION_TOKEN = role_response['Credentials']['SessionToken']
    else:
        ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
        SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
        SESSION_TOKEN = os.getenv('AWS_SESSION_TOKEN')

    return boto3.client(
        'dynamodb',
        aws_access_key_id=ACCESS_KEY_ID,
        aws_secret_access_key=SECRET_ACCESS_KEY,
        aws_session_token=SESSION_TOKEN
    )


def lambda_handler(event, context):
    ddb_client = _get_ddb_client()

    try:
        if 'LastEvaluatedKey' in event:
            print("continuing from {}".format(event['LastEvaluatedKey']))
            return {'LastEvaluatedKey': _query_dynamo(ddb_client, context, start_key=event['LastEvaluatedKey'])}
        else:
            print("starting to parse {}".format(DYNAMO_TABLE_NAME))
            return {'LastEvaluatedKey': _query_dynamo(ddb_client, context)}
    except Exception as e:
        raise e
