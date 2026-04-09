# AFinOps Tonder · Demo Contable

Demo funcional del proceso de cierre contable mensual.

## Stack
- **Backend**: Python 3.11 + FastAPI + SQLAlchemy + Alembic
- **Frontend**: React 18 + Vite + Tailwind CSS + Recharts
- **DB**: PostgreSQL 16 en `51.222.211.181:5432`
- **MongoDB**: Atlas (extracción de transacciones)

---

## Levantar el proyecto

### Backend

```bash
cd Backend

# 1. Crear entorno virtual e instalar dependencias
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

# 2. Correr migraciones (crea todas las tablas en PostgreSQL)
alembic upgrade head

# 3. Crear usuario admin por defecto
python seed.py
# → admin@tonder.io / Tonder2026!

# 4. Iniciar servidor
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API disponible en: http://localhost:8000
Docs Swagger: http://localhost:8000/docs

---

### Frontend

```bash
cd Front

npm install
npm run dev
```

App disponible en: http://localhost:3000

---

## Credenciales por defecto
| Campo | Valor |
|-------|-------|
| Email | admin@tonder.io |
| Password | Tonder2026! |

---

## Flujo de uso

1. **Login** → ingresa con admin@tonder.io
2. **Nueva corrida** → selecciona año, mes y adquirentes
3. **Sube archivos** → arrastra archivos Kushki (CSV/Excel) y Banregio (PDF/Excel/CSV)
4. **Ejecuta** → clic en "Ejecutar proceso"
5. **Monitorea** → observa el progreso por etapas en tiempo real
6. **Ver resultados** → FEES / Kushki / Banregio / Conciliaciones

---

## Variables de entorno clave (Backend/.env)

```env
DATABASE_URL=postgresql://tondeservice:...@51.222.211.181:5432/tondeservice
MONGO_URI=mongodb+srv://etl_simetrik:...@pdnserverlessinstance...
# AWS Settlements (placeholder — completar cuando estén disponibles)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SETTLEMENTS_TABLE=
```

---

## Estructura del proyecto

```
AFinOpsTonder/
├── Backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings desde .env
│   │   ├── database.py          # SQLAlchemy engine
│   │   ├── models/              # ORM models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── routers/             # auth / processes / files / results
│   │   ├── services/
│   │   │   ├── mongo_extractor.py   # Extracción MongoDB
│   │   │   ├── fees_processor.py    # Lógica FEES + recomputación
│   │   │   ├── kushki_parser.py     # Parser Kushki CSV/Excel
│   │   │   ├── banregio_parser.py   # Parser Banregio PDF/Excel
│   │   │   ├── conciliation_engine.py  # 3 conciliaciones
│   │   │   └── aws_settlements.py   # Placeholder AWS
│   │   └── core/                # security + deps
│   ├── alembic/                 # Migraciones
│   ├── requirements.txt
│   └── seed.py
└── Front/
    ├── src/
    │   ├── pages/               # Login, Dashboard, Processes, Results
    │   ├── components/          # Layout, Sidebar, UI
    │   ├── api/client.js        # Axios + endpoints
    │   └── hooks/useAuth.js
    └── package.json
```
