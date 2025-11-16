import json
import jwt
import os

JWT_SECRET = os.environ["JWT_SECRET"]

def lambda_handler(event, context):
    token = event["headers"].get("Authorization", "")
    token = token.replace("Bearer ", "")

    if not token:
        return deny("Token no proporcionado")

    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        
        return allow(decoded["userId"], decoded, event["methodArn"])
        
    except jwt.ExpiredSignatureError:
        return deny("Token expirado")
    except jwt.InvalidTokenError as e:
        return deny(f"Token inválido: {str(e)}")
    except Exception as e:
        return deny(f"Error validando token: {str(e)}")

def allow(principal_id, context, method_arn):
    """Retornar política IAM que PERMITE el acceso"""
    return {
        "principalId": principal_id,
        "context": context
    }

def deny(message):
    """Retornar política IAM que DENIEGA el acceso"""
    print(f"Acceso denegado: {message}")
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
