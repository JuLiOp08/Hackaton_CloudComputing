# AlertaUTEC

Backend serverless para la gestión de incidentes universitarios, autenticación, roles y notificaciones.

## Arquitectura
- AWS Lambda (Python 3.12)
- API Gateway REST
- DynamoDB (Usuarios, Incidentes, Historial-Incidente)
- SNS (Notificaciones)
- JWT para autenticación
- bcrypt para hashing

## Endpoints REST

### Usuarios
- **POST /usuarios/registro**
	- Registra usuario estudiante
	- Request: `{ "email": "usuario@utec.edu.pe", "password": "123456", "nombre": "Juan" }`
	- Response: `{ "success": true, "data": { "token": "..." } }`

- **POST /usuarios/login**
	- Inicia sesión
	- Request: `{ "email": "usuario@utec.edu.pe", "password": "123456" }`
	- Response: `{ "success": true, "data": { "token": "..." } }`

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
	- Listar incidentes activos
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

### Historial
- **GET /historial/listar?page=1&size=10**
	- Listar historial completo (paginado)
	- Headers: `Authorization: Bearer <token>`
	- Response: `{ "success": true, "data": [ ...historial ] }`

- **GET /historial/incidente?codigo_incidente=...**
	- Listar historial por incidente
	- Headers: `Authorization: Bearer <token>`
	- Response: `{ "success": true, "data": [ ...historial ] }`

### Administrativas
- **PUT /incidentes/estado**
	- Actualizar estado
	- Request: `{ "codigo_incidente": "...", "estado": "resuelto" }`
	- Headers: `Authorization: Bearer <token>`
	- Response: `{ "success": true, "data": { "codigo_incidente": "...", "estado": "resuelto" } }`

## Seguridad y Roles
- Todos los endpoints privados requieren JWT válido en el header Authorization.
- El JWT debe contener: userId, email, role.
- Solo el rol "autoridad" puede listar usuarios y administrar incidentes.

## Tablas DynamoDB
- **Usuarios**: email (PK), tenant_id (UUID), nombre, contraseña_hash, role, createdAt
- **Incidentes**: codigo_incidente (PK), ubicacion, descripcion, estado, fecha, tipo, urgencia, imagen, reportanteId, responsableId
- **Historial-Incidente**: codigo_incidente (PK), uuid_evento (SK), tiempo, encargado, estado, detalles

## Tipos de Incidentes
- Fuga de agua
- Piso mojado
- Daño en utilería de salón
- Daño infraestructura:
- Emergencia Medica
- Baño dañado


## Notificaciones SNS
- Al crear usuario
- Al crear incidente (a administradores)
- Al actualizar estado (al reportante)
- Al resolver incidente (al reportante)

## Deploy
1. Instala Serverless Framework
2. Configura credenciales AWS
3. Ejecuta `serverless deploy`

---
