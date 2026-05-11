"""
Minimal FastAPI teaching app for cloud evaluation.

This file is intentionally incomplete. Students must implement:
- Cloud SQL (PostgreSQL) integration
- Cloud Storage integration
- Firestore integration
"""

import os
import psycopg2

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from google.cloud import storage

load_dotenv()

app = FastAPI(title="Cloud Computing Evaluation API (Starter)")

# Configurar templates
templates = Jinja2Templates(directory="templates")

# Montar archivos estáticos (si los necesitamos después)
# app.mount("/static", StaticFiles(directory="static"), name="static")

# =========================
# DATABASE CONNECTION
# =========================

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

# conn = psycopg2.connect(
#     host=os.getenv("DB_HOST"),
#     port=os.getenv("DB_PORT"),
#     database=os.getenv("DB_NAME"),
#     user=os.getenv("DB_USER"),
#     password=os.getenv("DB_PASSWORD")
# )

# cursor = conn.cursor()

# cursor.execute("""
# CREATE TABLE IF NOT EXISTS products (
#     id SERIAL PRIMARY KEY,
#     name VARCHAR(255),
#     description TEXT,
#     price NUMERIC
# )
# """)

# conn.commit()


# =========================
# MODELS
# =========================

class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    price: float


class CommentCreate(BaseModel):
    author: str
    text: str


# =========================
# ENDPOINTS
# =========================

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
def health():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255),
            description TEXT,
            price NUMERIC
        )
        """)
        conn.commit()
        conn.close()
        return {
            "status": "ok",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "error",
            "database": str(e)
        }

@app.get("/health-page", response_class=HTMLResponse)
def health_page(request: Request):
    health_data = health()
    return templates.TemplateResponse("health.html", {"request": request, "health": health_data})


@app.post("/products")
def create_product(
    request: Request = None,
    name: str = Form(None),
    description: str = Form(None),
    price: float = Form(None),
    payload: ProductCreate = None
):
    # Determinar si es una petición de formulario HTML o JSON
    is_html_request = name is not None

    if is_html_request:
        # Validar datos del formulario
        if not name or not price:
            if request:
                return templates.TemplateResponse("products.html", {
                    "request": request,
                    "products": [],
                    "error": "Nombre y precio son requeridos"
                })
            raise HTTPException(status_code=400, detail="Nombre y precio son requeridos")

        product_data = ProductCreate(name=name, description=description, price=price)
    else:
        # Usar datos JSON
        if not payload:
            raise HTTPException(status_code=400, detail="Datos del producto requeridos")
        product_data = payload

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO products (name, description, price)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (product_data.name, product_data.description, product_data.price)
        )

        product_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        if is_html_request:
            # Redirigir a la página de productos
            return RedirectResponse(url="/products", status_code=303)

        return {
            "message": "Producto creado correctamente",
            "product_id": product_id
        }

    except Exception as e:
        if is_html_request and request:
            return templates.TemplateResponse("products.html", {
                "request": request,
                "products": [],
                "error": f"Error al crear producto: {str(e)}"
            })
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/products")
def list_products(request: Request = None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, description, price
            FROM products
            ORDER BY id
        """)

        products = cursor.fetchall()
        conn.close()

        result = []

        for product in products:
            result.append({
                "id": product[0],
                "name": product[1],
                "description": product[2],
                "price": float(product[3])
            })

        # Si es una petición desde navegador (tiene request), devolver HTML
        if request:
            return templates.TemplateResponse("products.html", {
                "request": request,
                "products": result,
                "error": None
            })

        # Si no, devolver JSON (para API)
        return result

    except Exception as e:
        if request:
            return templates.TemplateResponse("products.html", {
                "request": request,
                "products": [],
                "error": str(e)
            })
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/products/{product_id}/image")
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...)
):

    storage_client = storage.Client()

    bucket = storage_client.bucket(
        os.getenv("BUCKET_NAME")
    )

    blob_name = f"products/{product_id}/{file.filename}"

    blob = bucket.blob(blob_name)

    blob.upload_from_file(
        file.file,
        content_type=file.content_type
    )

    image_url = (
        f"https://storage.googleapis.com/"
        f"{bucket.name}/{blob_name}"
    )

    return {
        "message": "Imagen subida correctamente",
        "product_id": product_id,
        "filename": file.filename,
        "url": image_url
    }


@app.post("/products/{product_id}/comments")
def add_product_comment(product_id: int, payload: CommentCreate):

    return {
        "message": "Comentario registrado correctamente",
        "product_id": product_id,
        "author": payload.author,
        "text": payload.text
    }


@app.get("/audit/events")
def get_audit_events():

    return [
        {
            "product_id": 1,
            "author": "Jesus",
            "text": "Excelente producto"
        }
    ]