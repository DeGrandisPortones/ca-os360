## Backend

Este backend expone:

- `GET /api/health`
- `POST /api/login`
- `POST /api/transform`

`POST /api/login`
```json
{
  "username": "tu_usuario",
  "password": "tu_clave"
}
```

Respuesta:
```json
{
  "ok": true,
  "token": "..."
}
```

`POST /api/transform`
- Header: `Authorization: Bearer <token>`
- Form-data: `file` = archivo `.xls` o `.xlsx`
