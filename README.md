# AlertaUTEC

Backend serverless para la gestión de incidentes universitarios, autenticación, roles y notificaciones.

## Arquitectura
- AWS Lambda (Python 3.13)
- API Gateway REST
- DynamoDB (t_users, t_incidentes, t_historial)
- SNS (Notificaciones)
- JWT para autenticación
- bcrypt para hashing

## Lambdas Disponibles
- **Auth**: register_user, login_user, validate_token
- **Users**: get_user_by_id, list_users  
- **Incidentes**: create_incidente, list_incidentes_activos, list_incidentes_admin, get_incidente_by_id, update_estado_incidente
- **Historial**: list_historial, list_historial_by_incidente

## Endpoints REST

### Autenticación
- **POST /usuarios/registro**
	- Registra usuario (estudiante o autoridad)
	- Request: `{ "email": "usuario@utec.edu.pe", "password": "123456", "nombre": "Juan", "role": "estudiante" }`
	- Response: `{ "success": true, "data": { "token": "..." } }`

- **POST /usuarios/login**
	- Inicia sesión
	- Request: `{ "email": "usuario@utec.edu.pe", "password": "123456" }`
	- Response: `{ "success": true, "data": { "token": "..." } }`

### Usuarios
- **GET /usuarios/buscar?userId=...**
	- Busca usuario por UUID
	- Headers: `Authorization: Bearer <token>`
	- Response: `{ "success": true, "data": { ...usuario } }`

- **GET /usuarios/listar**
	- Listar todos los usuarios (solo autoridad)
	- Headers: `Authorization: Bearer <token>`
	- Response: `{ "success": true, "data": [ ...usuarios ] }`

### Incidentes
- **POST /incidentes/crear**
	- Crear incidente
	- Request: `{ "ubicacion": "Aula 101", "descripcion": "Fuga de agua", "tipo": "Fuga de agua", "urgencia": "alta", "imagen": "url" }`
	- Headers: `Authorization: Bearer <token>`
	- Response: `{ "success": true, "data": { "codigo_incidente": "...", "estado": "pendiente", "fecha": "..." } }`

- **GET /incidentes/activos**
	- Listar incidentes activos (pendiente, en_proceso)
	- Headers: `Authorization: Bearer <token>`
	- Response: `{ "success": true, "data": [ ...incidentes ] }`

- **GET /incidentes/admin**
	- Listar todos los incidentes (solo autoridad)
	- Headers: `Authorization: Bearer <token>`
	- Response: `{ "success": true, "data": [ ...incidentes ] }`

- **GET /incidentes/buscar?codigo_incidente=...**
	- Obtener incidente por ID
	- Headers: `Authorization: Bearer <token>`
	- Response: `{ "success": true, "data": { ...incidente } }`

- **PUT /incidentes/estado**
	- Actualizar estado (solo autoridad)
	- Request: `{ "codigo_incidente": "...", "estado": "resuelto" }`
	- Headers: `Authorization: Bearer <token>`
	- Response: `{ "success": true, "data": { "codigo_incidente": "...", "estado": "resuelto" } }`

### Historial
- **GET /historial/listar?page=1&size=10**
	- Listar historial completo (paginado)
	- Headers: `Authorization: Bearer <token>`
	- Response: `{ "success": true, "data": [ ...historial ] }`

- **GET /historial/incidente?codigo_incidente=...**
	- Listar historial por incidente
	- Headers: `Authorization: Bearer <token>`
	- Response: `{ "success": true, "data": [ ...historial ] }`

## Seguridad y Roles
- Todos los endpoints privados requieren JWT válido en el header Authorization.
- El JWT contiene: userId, email, role, exp (48 horas).
- Solo el rol "autoridad" puede administrar incidentes y listar usuarios.

## Tablas DynamoDB
- **t_users**: email (PK), tenant_id (UUID), nombre, contraseña_hash, role, createdAt
- **t_incidentes**: codigo_incidente (PK), ubicacion, descripcion, estado, fecha, tipo, urgencia, imagen, reportanteId, responsableId
- **t_historial**: codigo_incidente (PK), uuid_evento (SK), tiempo, encargado, estado, detalles

## Tipos de Incidentes Válidos
- Fuga de agua
- Piso mojado
- Daño en utilería de salón
- Daño infraestructura
- Objeto perdido
- Emergencia médica
- Baño dañado

## Estados de Incidentes
- **pendiente**: Recién creado, sin atender
- **en_proceso**: Siendo atendido
- **resuelto**: Completado y cerrado

## Notificaciones SNS
- Al crear usuario
- Al crear incidente (a administradores)
- Al actualizar estado (al reportante)

## Deploy
1. Instala Serverless Framework
2. Configura credenciales AWS
3. Ejecuta `serverless deploy`

---
