# CotizIA · Asistente web para consultas y presupuestos 24/7

Avance (semana 8) del curso de IA y Machine Learning, cliente 9. IA clásica: agente basado en objetivos con
sistema experto (26 reglas, encadenamiento hacia adelante, traza explicable). Listo para crecer a la semana 16.

## Estructura
```
app.py                 Interfaz web (Streamlit). Solo dibuja; no tiene lógica de negocio.
servicio.py            Une motor + registro. Mañana una API REST llamaría aquí.
config.py              Lee data/negocio.json (IGV, envío, descuentos, umbral, textos).
motor/                 Catálogo, reglas R1–R26, motor de inferencia, cotizador (Decimal), anonimizador.
  clasificadores.py    Línea base (alternativa A) y ClasificadorML (semana 16).
infra/registro.py      Registro anonimizado: CSV, SQLite, Firestore o memoria.
data/                  catalogo.csv y negocio.json (EJEMPLO sintético: reemplazar con datos de la clienta).
tests/casos_prueba.py  12 casos documentados + reporte de métricas.
```

## Correr local
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py                                   # http://localhost:8501
python consola.py                                      # chat por consola, sin Streamlit
```

## Pruebas y tabla de resultados para el documento
```bash
python -m tests.casos_prueba     # imprime la tabla de la sección 6
pip install pytest && pytest     # las mismas comprobaciones como pruebas
```

## Desplegar en Google Cloud Run
```bash
gcloud config set project TU_PROYECTO
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com firestore.googleapis.com
gcloud firestore databases create --location=southamerica-east1     # una sola vez

gcloud run deploy cotizia --source . --region southamerica-east1 --allow-unauthenticated \
  --session-affinity --min-instances 0 --max-instances 5 \
  --set-env-vars COTIZIA_STORAGE=firestore,COTIZIA_WHATSAPP=519XXXXXXXX,COTIZIA_CORREO=correo@dominio.com
```
Si el despliegue falla al guardar, dale permiso a la cuenta de servicio de Cloud Run:
`roles/datastore.user`. Cloud Run tiene disco efímero: por eso en la nube se usa Firestore, no CSV.

## Escalabilidad (por qué crece sin reescribir)
- **Motor sin estado**: el estado vive en `Conversacion` (sesión del usuario). Cloud Run puede levantar varias instancias.
- **Rubro**: se cambia editando `data/catalogo.csv` y `data/negocio.json`; el código no se toca.
- **Registro**: contrato único `guardar(fila)`; cambiar de CSV a Firestore es una variable de entorno.
- **Semana 16**: el registro ya guarda `mensaje_anonimizado` y `etiqueta_revisada` (corrígela a mano) → ese CSV es el dataset de ≥300 mensajes.
  Entrena un Pipeline (TF-IDF + Naive Bayes/SVM con `probability=True`), guárdalo con joblib y arranca con
  `COTIZIA_MODELO_ML=modelo.joblib`: la regla `ML` decide la intención y, si no llega al umbral, caen las reglas R1–R12 (modo híbrido).
  La cotización sigue siendo determinista.

## Privacidad (Ley N.° 29733)
Se enmascaran teléfono, DNI y correo antes de registrar (R25). Los nombres propios no se detectan automáticamente:
el aviso pide no escribirlos. Se informa al usuario que habla con un asistente automático (R26).
