import json
import jwt
import os

JWT_SECRET = os.environ.get("JWT_SECRET", "alerta-utec-secret-key-2024")

def lambda_handler(event, context):
    print("Authorizer event:", json.dumps(event))
    
    try:
        if not auth_token:
            print("No authorizationToken provided")
            return generate_policy('anonymous', 'Deny', event.get('methodArn'))
        
        # Remover 'Bearer ' si está presente
        if auth_token.startswith('Bearer '):
            token = auth_token[7:]
        else:
            token = auth_token
        
        print(f"Validating token: {token[:20]}...")
        
        # Decodificar el token JWT
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        user_id = decoded.get('userId', 'unknown')
        
        print(f"Token validado para usuario: {user_id}")
        
        # Devolver política que PERMITE el acceso
        return generate_policy(user_id, 'Allow', event.get('methodArn'), decoded)
        
    except jwt.ExpiredSignatureError:
        print("Token expirado")
        return generate_policy('anonymous', 'Deny', event.get('methodArn'))
    except jwt.InvalidTokenError as e:
        print(f"Token inválido: {str(e)}")
        return generate_policy('anonymous', 'Deny', event.get('methodArn'))
    except Exception as e:
        print(f"Error validando token: {str(e)}")
        return generate_policy('anonymous', 'Deny', event.get('methodArn'))

def generate_policy(principal_id, effect, resource, context=None):
    """Genera la política IAM para API Gateway"""
    
    if resource:
        if not resource.endswith('/*'):
            resource = resource.split('/')[0] + '/*'
    else:
        resource = '*'
    
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
    }
    
    if context and effect == 'Allow':
        policy['context'] = {
            'userId': str(context.get('userId', '')),
            'email': str(context.get('email', '')),
            'role': str(context.get('role', 'estudiante'))
        }
    
    print(f"📋 Policy generated: {effect} for {principal_id}")
    return policy
