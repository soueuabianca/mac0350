from typing import Optional
from fastapi import FastAPI, Request, Form, HTTPException, Depends, Cookie, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from sqlmodel import Session, select, col

from models import Usuario, Tarefa
from database import engine, create_db_and_tables

@asynccontextmanager
async def initFunction(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=initFunction)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory=["templates"])


def obter_usuario_logado(session_user: Optional[str] = Cookie(None)):
    if not session_user:
        raise HTTPException(status_code=401, detail="Acesso negado")
    with Session(engine) as session:
        usuario = session.get(Usuario, int(session_user))
        if not usuario:
            raise HTTPException(status_code=401, detail="Sessão inválida")
        return usuario

def obter_tarefas_paginadas(session: Session, usuario_id: int, busca: str | None = '', tipo_busca: str | None = '', prioridade_busca: str | None = '', pagina: int = 1):
    query = select(Tarefa).where(Tarefa.usuario_id == usuario_id)
    
    if busca:
        query = query.where(col(Tarefa.titulo).contains(busca))
    if tipo_busca:
        query = query.where(Tarefa.tipo == tipo_busca)
    if prioridade_busca:
        query = query.where(Tarefa.prioridade == prioridade_busca)
        
    query = query.order_by(col(Tarefa.id).desc())
    
    total_tarefas = len(session.exec(query).all())
    total_paginas = max(1, (total_tarefas + 3) // 4)
        
    if pagina > total_paginas:
        pagina = total_paginas
    
    offset = (pagina - 1) * 4
    tarefas_db = session.exec(query.offset(offset).limit(5)).all()
    
    tem_mais = len(tarefas_db) > 4
    tarefas = tarefas_db[:4]
    
    return tarefas, tem_mais, total_paginas, pagina


@app.get("/login", response_class=HTMLResponse)
def tela_login(request: Request):
    return templates.TemplateResponse(request, "login.html", {})

@app.post("/login")
def fazer_login(nome: str = Form(...)):
    with Session(engine) as session:
        query = select(Usuario).where(Usuario.nome == nome)
        usuario = session.exec(query).first()
        
        if not usuario:
            usuario = Usuario(nome=nome, bio="Escreva a sua bio no perfil.", curso="Sem curso")
            session.add(usuario)
            session.commit()
            session.refresh(usuario)
        
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(key="session_user", value=str(usuario.id))
        return response

@app.post("/logout")
def fazer_logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session_user")
    return response

@app.get("/", response_class=HTMLResponse)
def index(request: Request, session_user: Optional[str] = Cookie(None), busca: str | None = '', tipo_busca: str | None = '', prioridade_busca: str | None = '', pagina: int = 1):
    if not session_user:
        return RedirectResponse(url="/login")
        
    with Session(engine) as session:
        usuario = session.get(Usuario, int(session_user))
        if not usuario:
            response = RedirectResponse(url="/login")
            response.delete_cookie("session_user")
            return response

        tarefas, tem_mais, total_paginas, pagina_atual = obter_tarefas_paginadas(
            session, usuario.id, busca, tipo_busca, prioridade_busca, pagina
        )

        contexto = {
            "tarefas": tarefas, "busca": busca, "tipo_busca": tipo_busca, 
            "prioridade_busca": prioridade_busca, "pagina": pagina_atual, 
            "tem_mais": tem_mais, "total_paginas": total_paginas
        }

        if "HX-Request" in request.headers:
            return templates.TemplateResponse(request, "lista_tarefas.html", contexto)
        
        contexto["usuario"] = usuario
        return templates.TemplateResponse(request, "index.html", contexto)

@app.get("/perfil", response_class=HTMLResponse)
def perfil(request: Request, usuario: Usuario = Depends(obter_usuario_logado)):
    return templates.TemplateResponse(request, "perfil.html", {"usuario": usuario})

@app.put("/perfil", response_class=HTMLResponse)
def atualizar_perfil(request: Request, usuario: Usuario = Depends(obter_usuario_logado), nome: str = Form(...), curso: str = Form(...), bio: str = Form(...)):
    with Session(engine) as session:
        usuario_db = session.get(Usuario, usuario.id)
        usuario_db.nome = nome
        usuario_db.curso = curso
        usuario_db.bio = bio
        
        session.add(usuario_db)
        session.commit()
        
        return templates.TemplateResponse(request, "perfil.html", {"usuario": usuario_db})

@app.post("/tarefas", response_class=HTMLResponse)
def criar_tarefa(request: Request, usuario: Usuario = Depends(obter_usuario_logado), titulo: str = Form(...), tipo: str = Form(...), prioridade: str = Form(...)):
    with Session(engine) as session:
        nova_tarefa = Tarefa(titulo=titulo, tipo=tipo, prioridade=prioridade, usuario_id=usuario.id)
        session.add(nova_tarefa)
        session.commit()
        
        tarefas, tem_mais, total_paginas, pagina_atual = obter_tarefas_paginadas(session, usuario.id)
        
        return templates.TemplateResponse(request, "lista_tarefas.html", {
            "tarefas": tarefas, "busca": "", "tipo_busca": "", 
            "prioridade_busca": "", "pagina": pagina_atual, 
            "tem_mais": tem_mais, "total_paginas": total_paginas
        })

@app.delete("/tarefas", response_class=HTMLResponse)
def deletar_tarefa(request: Request, id: int, usuario: Usuario = Depends(obter_usuario_logado), busca: str | None = '', tipo_busca: str | None = '', prioridade_busca: str | None = '', pagina: int = 1):
    with Session(engine) as session:
        query = select(Tarefa).where(Tarefa.id == id, Tarefa.usuario_id == usuario.id)
        tarefa = session.exec(query).first()
        
        if not tarefa:
            raise HTTPException(404, "Tarefa não encontrada ou não pertence ao usuário")
        
        session.delete(tarefa)
        session.commit()
        
        tarefas, tem_mais, total_paginas, pagina_atual = obter_tarefas_paginadas(
            session, usuario.id, busca, tipo_busca, prioridade_busca, pagina
        )
        
        return templates.TemplateResponse(request, "lista_tarefas.html", {
            "tarefas": tarefas, "busca": busca, "tipo_busca": tipo_busca, 
            "prioridade_busca": prioridade_busca, "pagina": pagina_atual, 
            "tem_mais": tem_mais, "total_paginas": total_paginas
        })