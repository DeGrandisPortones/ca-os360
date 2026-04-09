# DFlex Transformador - Render + Vercel

Proyecto preparado para publicar:

- `backend/` -> API Flask para Render
- `frontend/` -> Frontend estático para Vercel

## Flujo

1. El usuario inicia sesión desde el frontend.
2. El frontend envía usuario y contraseña al backend.
3. El backend valida contra variables de entorno y devuelve un token simple firmado.
4. El frontend usa ese token para enviar el archivo `.xls` o `.xlsx`.
5. El backend transforma el archivo con la lógica original y devuelve `Lista de import.xlsx`.

## Variables de entorno del backend

Copiá `backend/.env.example` como referencia. En Render configurá:

- `APP_USERNAME`
- `APP_PASSWORD`
- `SECRET_KEY`

Opcionales:

- `TOKEN_MAX_AGE_SECONDS` (por defecto 28800)
- `MAX_CONTENT_LENGTH_MB` (por defecto 20)
- `CORS_ORIGINS` (solo si no usás rewrite desde Vercel)

## Deploy recomendado

### Backend en Render

Root Directory: `backend`

Si usás Docker:
- Render detecta `Dockerfile`

Si usás entorno Python:
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`

### Frontend en Vercel

Root Directory: `frontend`

Antes de publicar, editá `frontend/vercel.json` y reemplazá:

- `https://YOUR-RENDER-BACKEND.onrender.com`

por la URL real del backend en Render.

El frontend llama a `/api/login` y `/api/transform`.
Vercel reescribe esas rutas al backend para evitar CORS en el navegador.

## Desarrollo local

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

### Frontend
Podés abrir `frontend/index.html` directo en navegador para pruebas simples.
Para que funcione contra backend local, conviene servir el frontend con un servidor estático y adaptar `vercel.json` solo para deploy, o publicar primero backend y luego frontend.

## Estructura

```text
backend/
  app.py
  transformar_simple.py
  requirements.txt
  Dockerfile
  .env.example
  forzar_D.txt
frontend/
  index.html
  app.js
  styles.css
  vercel.json
```


## Subir a GitHub

### Opción recomendada: un solo repositorio con backend y frontend

1. Creá un repositorio vacío en GitHub, por ejemplo:
   - `dflex-transformador-online`

2. Descargá y descomprimí este proyecto.

3. Desde la carpeta raíz del proyecto ejecutá:

```bash
git init
git branch -M main
git add .
git commit -m "Initial commit - Render backend + Vercel frontend"
git remote add origin https://github.com/TU-USUARIO/dflex-transformador-online.git
git push -u origin main
```

### Si preferís usar GitHub Desktop

- File -> Add local repository
- Elegí esta carpeta
- Publish repository
- Luego conectá:
  - Render al directorio `backend`
  - Vercel al directorio `frontend`

## Deploy desde GitHub

### Render
- New Web Service
- Seleccioná el repo
- Root Directory: `backend`

### Vercel
- Add New Project
- Import Git Repository
- Root Directory: `frontend`

## Variables necesarias en Render

- `APP_USERNAME`
- `APP_PASSWORD`
- `SECRET_KEY`

## Ajuste necesario antes del deploy del frontend

Editá `frontend/vercel.json` y reemplazá:

- `https://YOUR-RENDER-BACKEND.onrender.com`

por la URL real de tu backend en Render.
asdasd

## Cambio aplicado

- El backend ahora soporta ambos formatos de origen:
  - columnas combinadas: `Precio Unitario - Medida` y `Precio Unitario - Medida.1`
  - columnas separadas: `Precio Unitario`, `Medida`, `Precio Unitario.1`, `Medida.1`
