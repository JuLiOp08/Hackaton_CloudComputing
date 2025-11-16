import json
import jwt
import os

JWT_SECRET = os.environ["JWT_SECRET"]

def lambda_handler(event, context):
    token = event["headers"].get("Authorization", "")
    token = token.replace("Bearer ", "")

    if not token:
        return deny("missing token")

    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return deny("expired token")
    except Exception as e:
        return deny("invalid token")

    # Claims que quieres enviar al backend
    return allow(decoded["userId"], decoded)


def allow(principalId, context):
    return {
        "principalId": principalId,
        "context": context
    }


def deny(message):
    return {
        "principalId": "anonymous",
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": "Deny",
                    "Resource": "*"
                }
            ]
        }
    }
