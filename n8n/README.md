# Alertas por correo con n8n

Este flujo envía por **Gmail** un correo por cada turno de la planta que tenga ciclos en **riesgo Alto** de falla.

```
Cada minuto - Leer CSV de alertas - Extraer filas - Elegir siguiente turno - Enviar correo (Gmail) - Registrar envío
```

- Lee `data/processed/alertas_por_turno.csv` (lo genera `notebooks/04_alertas.ipynb`).
- **Cada minuto real envía el siguiente turno** que todavía no se haya enviado. Así simula una planta en vivo.
- Por defecto se detiene a los **5 correos** (demo corta). Con `LIMITE_CORREOS_DEMO=0` hace el **flujo completo**:
  los 108 correos en ~1 h 50 min (ver Paso 7).
- **Recuerda** los turnos ya enviados. Si un envío falla, no lo anota y lo reintenta al minuto siguiente.

---

## Qué necesitas

| Requisito | Para qué |
|---|---|
| **Docker Desktop** abierto | Ejecuta n8n en un contenedor |
| **Cuenta de Gmail** con verificación en dos pasos | Envía los correos |
| Los notebooks **01, 03 y 04** ejecutados | Generan el CSV de alertas |

---

## Paso 1 · Crear una contraseña de aplicación de Gmail

n8n **no usa tu contraseña normal** de Gmail, sino una **contraseña de aplicación**: un código de 16 letras solo para n8n,
que puedes borrar cuando quieras.

1. Entra a tu cuenta de Google → **Seguridad**.
2. Activa la **Verificación en dos pasos** (si no la tienes).
3. Busca **Contraseñas de aplicaciones** (o entra directo a `https://myaccount.google.com/apppasswords`).
4. Escribe un nombre, por ejemplo `n8n planta`, y presiona **Crear**.
5. Copia el código de 16 letras. **No lo guardes en ningún archivo del proyecto**: solo lo pegarás dentro de n8n (Paso 4).

---

## Paso 2 · Poner tus correos en el archivo `.env`

Tus correos **no van en el código**, van en un archivo `.env` que **nunca se sube a GitHub** (está en `.gitignore`).

1. En la raíz del proyecto, copia `.env.example` y renombra la copia a **`.env`**. En la terminal de VS Code:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Abre `.env` y cambia **solo estas dos líneas**:

   ```
   CORREO_REMITENTE=tu_cuenta@gmail.com      ← la cuenta de Gmail del Paso 1
   CORREO_DESTINO=destino@ejemplo.com        ← el correo que recibirá las alertas (puede ser el mismo)
   ```

3. Guarda el archivo. (`LIMITE_CORREOS_DEMO` y `ZONA_HORARIA` puedes dejarlos como están.)

---

## Paso 3 · Iniciar n8n con Docker

1. Abre **Docker Desktop** y espera a que diga que el motor está funcionando (*Engine running*).
2. En la terminal de VS Code, **en la carpeta del proyecto**:

   ```powershell
   docker compose up -d
   ```

   La primera vez descarga la imagen de n8n (puede tardar unos minutos).
3. Revisa que esté funcionando:

   ```powershell
   docker compose ps
   ```

   Debe aparecer `planta-n8n` con estado `running` / `Up`.
4. Abre **http://localhost:5678** en el navegador.
5. La primera vez, n8n pide crear una **cuenta de propietario**. Es una cuenta **local, solo en tu computadora**: elige el correo y la contraseña que quieras.

---

## Paso 4 · Crear la credencial de Gmail (SMTP) en n8n

1. En n8n: botón **＋** de la barra lateral izquierda (arriba) → **Credential**.
2. Busca y elige **SMTP**.
3. Llena los campos:

   | Campo | Valor |
   |---|---|
   | User | tu cuenta de Gmail (la de `CORREO_REMITENTE`) |
   | Password | la **contraseña de aplicación** del Paso 1 (sin espacios) |
   | Host | `smtp.gmail.com` |
   | Port | `465` |
   | SSL/TLS | **activado** |

4. Guarda. n8n prueba la conexión y debe decir que funcionó.

> La contraseña queda **cifrada dentro de n8n** (en el volumen de Docker `n8n_datos`). No está en el proyecto ni en GitHub.

---

## Paso 5 · Importar el flujo

1. En n8n: botón **＋** de la barra lateral izquierda → **Workflow**.
2. En el menú **⋯** (arriba a la derecha) → **Import from File…** → elige `n8n/alertas_por_turno.json` de este proyecto.
3. Abre el nodo **Enviar correo (Gmail)** y en **Credential to connect with** elige la credencial SMTP del Paso 4.
4. No hay botón *Save*: n8n **guarda el flujo automáticamente** (si quieres asegurarte, presiona **Ctrl + S**).

> En los campos *From Email* y *To Email* aparece en rojo `[ERROR: not accessible via UI, please run node]`.
> **Es normal**: por seguridad n8n no muestra en pantalla los valores de `.env`, pero sí los usa al ejecutar.

---

## Paso 6 · Probar

1. Presiona **Execute** (abajo al centro del lienzo).
2. Debe llegar **un correo** a `CORREO_DESTINO`: *⚠️ 1 alerta de riesgo ALTO · Turno Mañana · 2026-09-01*
   (si no está en la bandeja de entrada, revisa *Spam*).
3. Cada nodo muestra un ✔ verde y cuántos elementos pasaron por él:
   `Extraer filas` → **108 items** (todos los turnos) y `Elegir siguiente turno` → **1 item** (el que se envía).

> En las **pruebas manuales** n8n no guarda la memoria de lo enviado, así que cada prueba manda **el mismo primer correo**. Es normal.

---

## Paso 7 · Activar (la demostración "en vivo")

1. Presiona **Publish** (arriba a la derecha). En n8n 2.x, publicar es lo que **activa** el flujo.
   n8n pide un nombre de versión, por ejemplo `Demo alertas por turno`, y presiona **Publish**.
2. Desde ese momento, **cada minuto llega el correo del siguiente turno**.
3. Al llegar al límite (5 por defecto) el flujo sigue corriendo, pero ya no manda nada.

### Demo corta o flujo completo

El límite se controla con **una línea de `.env`**:

| `LIMITE_CORREOS_DEMO` | Qué pasa |
|---|---|
| `5` (por defecto) | Envía los 5 primeros turnos (~5 min) y se detiene |
| `20`, `50`… | Envía esa cantidad de turnos |
| `0` | **Flujo completo**: los 108 turnos (~1 h 50 min) |

Para cambiarlo: edita `.env`, guarda y reinicia n8n para que lea el nuevo valor:

```powershell
docker compose up -d --force-recreate
```

Si ya se enviaron 5 y cambias a `0`, **continúa desde el turno 6**.

**Para detenerlo:** despublica el flujo (flecha **▾** junto a *Publish*). Para apagar n8n por completo:

```powershell
docker compose down
```

Tus credenciales y flujos **no se pierden**: quedan en el volumen `n8n_datos` y vuelven con `docker compose up -d`.

**Para repetir la demostración desde el primer turno:** borra el flujo en n8n e impórtalo otra vez (la memoria de envíos se guarda dentro del flujo).

---

