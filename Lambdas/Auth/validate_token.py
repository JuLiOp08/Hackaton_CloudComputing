import json
import jwt
import os

JWT_SECRET = os.environ.get("JWT_SECRET", "alerta-utec-secret-key-2024")

def lambda_handler(event, context):
    try:
        headers = event.get("headers", {})
        # Manejar tanto Authorization como authorization (case-insensitive)
        auth_header = headers.get("Authorization") or headers.get("authorization", "")
        token = auth_header.replace("Bearer ", "").replace("bearer ", "")

        if not token:
            return deny("Token no proporcionado")
        
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        
        # Crear política IAM que permite el acceso
        policy = {
            "principalId": decoded["userId"],
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "execute-api:Invoke",
                        "Effect": "Allow",
                        "Resource": event.get("methodArn", "*")
                    }
                ]
            },
            "context": {
                "userId": str(decoded["userId"]),
                "email": str(decoded["email"]),
                "role": str(decoded["role"])
            }
        }
        return policy
        
    except jwt.ExpiredSignatureError:
        return deny("Token expirado")
    except jwt.InvalidTokenError as e:
        return deny(f"Token inválido: {str(e)}")
    except Exception as e:
        return deny(f"Error validando token: {str(e)}")

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
