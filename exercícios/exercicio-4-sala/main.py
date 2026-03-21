from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

# Banco de dados em memória (lista simples)
db_usuarios = []

# Modelo Pydantic para validar o corpo do POST
class Usuario(BaseModel):
    nome: str
    idade: int

# --- 1. Rota GET '/' (Renderiza o HTML) ---
@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js"></script>
        <script src="https://unpkg.com/htmx.org@1.9.12/dist/ext/json-enc.js"></script>
        <title>Requests</title>
        <style>
            body { display: flex; gap: 2.5vw; justify-content: center; min-height: 90vh; background-color: #292827; color: #e0e0e0; font-family: sans-serif; }
            .secao-interacao, .secao-respostas { border: 2px solid #ff690a; border-radius: 15px; padding: 20px; width: 50%; height: auto; }
            .secao-interacao, form { display: flex; flex-direction: column; }
            #json-insert { color: #ff690a; font-size: xx-large; word-break: break-all; }
            label { margin-top: 15px; margin-bottom: 5px; font-weight: bold; color: #ff690a; }
            input[type="text"], input[type="number"] { background-color: #1e1e1e; border: 1px solid #444; border-radius: 8px; padding: 12px 15px; color: #e0e0e0; }
            input[type="submit"], button { margin-top: 20px; padding: 12px; border-radius: 8px; border: none; background-color: #ff690a; color: #fff; font-weight: bold; cursor: pointer; }
            hr { border: 0; border-top: 1px solid #444; margin: 25px 0; }
        </style>
    </head>
    <body>
        <div class="secao-interacao">
            <h1>Requests</h1>
            <form hx-post="/users" hx-ext="json-enc" hx-target="#json-insert" hx-swap="innerHTML">  
                <label for="nome">Nome do usuário</label>
                <input type="text" name="nome" required>
                <label for="idade">Idade do usuário</label>
                <input type="number" name="idade" required>
                <input type="submit" value="Enviar">
            </form>
            <hr>
            <input type="number" name="index" placeholder="Índice do usuário"
                   hx-get="/users" hx-trigger="input changed, delay:500ms" hx-target="#json-insert">
            <hr>
            <button hx-get="/users" hx-target="#json-insert">Obter todos os usuários</button>
            <hr>
            <button hx-delete="/users" hx-target="#json-insert">Apagar todos os usuários</button>
        </div>
        <div class="secao-respostas">
            <h1>Respostas</h1>
            <div id="json-insert"></div>
        </div>
    </body>
    </html>
    """

# --- 2. Rota POST '/users' (Adiciona usuário) ---
@app.post("/users")
async def create_user(user: Usuario):
    db_usuarios.append(user)
    return {"message": "Usuário adicionado!", "user": user}

# --- 3. Rota GET '/users' (Lê lista ou índice) ---
@app.get("/users")
async def get_users(index: Optional[int] = Query(None)):
    if index is not None:
        if 0 <= index < len(db_usuarios):
            return db_usuarios[index]
        return {"error": "Índice fora do alcance"}
    return db_usuarios

# --- 4. Rota DELETE '/users' (Limpa a lista) ---
@app.delete("/users")
async def delete_users():
    db_usuarios.clear()
    return {"message": "Todos os usuários foram removidos."}