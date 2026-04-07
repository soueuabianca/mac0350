from typing import Optional
from fastapi import FastAPI, Request, Form, HTTPException, Depends, Cookie, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

from models import Usuario, Tarefa
from database import engine, create_db_and_tables

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory=["templates"])

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

def obter_usuario_logado(session_user: Optional[str] = Cookie(None)):
    if not session_user or session_user == "":
        raise HTTPException(status_code=401, detail="Acesso negado")
    with Session(engine) as session:
        usuario = session.get(Usuario, int(session_user))
        if not usuario:
            raise HTTPException(status_code=401, detail="Sessão inválida")
        return usuario

def obter_tarefas(session: Session, usuario_id: int, busca: str = '', tipo_busca: str = '', prioridade_busca: str = ''):
    query = select(Tarefa).where(Tarefa.usuario_id == usuario_id)
    
    if busca:
        query = query.where(Tarefa.titulo.contains(busca))
    if tipo_busca:
        query = query.where(Tarefa.tipo == tipo_busca)
    if prioridade_busca:
        query = query.where(Tarefa.prioridade == prioridade_busca)
        
    return session.exec(query).all()

@app.get("/login", response_class=HTMLResponse)
def tela_login(request: Request):
    return templates.TemplateResponse(request, "login.html", {})

@app.post("/login")
def fazer_login(request: Request, nome: str = Form(...)):
    with Session(engine) as session:
        query = select(Usuario).where(Usuario.nome == nome)
        usuario = session.exec(query).first()
        
        if not usuario:
            usuario = Usuario(nome=nome, bio="Escreva a sua bio no perfil.", curso="Sem curso")
            session.add(usuario)
            session.commit()
            session.refresh(usuario)
        
        tarefas = obter_tarefas(session, usuario.id)
        contexto = {
            "request": request, 
            "usuario": usuario, 
            "tarefas": tarefas, 
            "busca": "", "tipo_busca": "", "prioridade_busca": ""
        }
        response = templates.TemplateResponse(request, "index.html", contexto)
        response.set_cookie(key="session_user", value=str(usuario.id))
        return response

@app.post("/logout")
def fazer_logout(request: Request):
    response = templates.TemplateResponse(request, "login.html", {})
    response.set_cookie(key="session_user", value="")
    return response

@app.get("/", response_class=HTMLResponse)
def index(request: Request, session_user: Optional[str] = Cookie(None), busca: str = '', tipo_busca: str = '',
           prioridade_busca: str = '', pagina: int = 1):
    if not session_user or session_user == "":
        return templates.TemplateResponse(request, "login.html", {})
        
    with Session(engine) as session:
        usuario = session.get(Usuario, int(session_user))
        if not usuario:
            return templates.TemplateResponse(request, "login.html", {})

        tarefas, tem_mais, total_paginas, pagina_atual = obter_tarefas_paginadas(
            session, usuario.id, busca, tipo_busca, prioridade_busca, pagina
        )

        contexto = {
            "request": request, "tarefas": tarefas, "busca": busca, 
            "tipo_busca": tipo_busca, "prioridade_busca": prioridade_busca,
            "pagina": pagina_atual, "tem_mais": tem_mais, "total_paginas": total_paginas,
            "usuario": usuario
        }

        if "HX-Request" in request.headers:
            return templates.TemplateResponse(request, "lista_tarefas.html", contexto)
        
        return templates.TemplateResponse(request, "index.html", contexto)

@app.get("/tarefas", response_class=HTMLResponse)
def carregar_lista_htmx(request: Request, usuario: Usuario = Depends(obter_usuario_logado)):
    with Session(engine) as session:
        tarefas, tem_mais, total_paginas, pagina = obter_tarefas_paginadas(session, usuario.id)
        
        return templates.TemplateResponse(request, "lista_tarefas.html", {
            "request": request, 
            "tarefas": tarefas,
            "pagina": pagina,
            "total_paginas": total_paginas,
            "tem_mais": tem_mais,
            "busca": "", "tipo_busca": "", "prioridade_busca": ""
        })

@app.get("/perfil", response_class=HTMLResponse)
def perfil(request: Request, usuario: Usuario = Depends(obter_usuario_logado)):
    return templates.TemplateResponse(request, "perfil.html", {"usuario": usuario})

@app.patch("/perfil", response_class=HTMLResponse)
def atualizar_perfil(request: Request, usuario: Usuario = Depends(obter_usuario_logado), nome: str = Form(...),
                      curso: str = Form(...), bio: str = Form(...)):
    with Session(engine) as session:
        usuario_db = session.get(Usuario, usuario.id)
        usuario_db.nome = nome
        usuario_db.curso = curso
        usuario_db.bio = bio
        
        session.add(usuario_db)
        session.commit()
        session.refresh(usuario_db)
        
        return templates.TemplateResponse(request, "perfil.html", {"usuario": usuario_db})

@app.post("/tarefas", response_class=HTMLResponse)
def criar_tarefa(request: Request, usuario: Usuario = Depends(obter_usuario_logado), titulo: str = Form(...), tipo: str = Form(...), prioridade: str = Form(...)):
    with Session(engine) as session:
        nova_tarefa = Tarefa(titulo=titulo, tipo=tipo, prioridade=prioridade, usuario_id=usuario.id)
        session.add(nova_tarefa)
        session.commit()
        
        tarefas, tem_mais, total_paginas, pagina = obter_tarefas_paginadas(session, usuario.id)
        
        return templates.TemplateResponse(request, "lista_tarefas.html", {
            "request": request, 
            "tarefas": tarefas,
            "pagina": pagina,
            "total_paginas": total_paginas,
            "tem_mais": tem_mais,
            "busca": "", "tipo_busca": "", "prioridade_busca": ""
        })

@app.delete("/tarefas", response_class=HTMLResponse)
def deletar_tarefa(request: Request, id: int, usuario: Usuario = Depends(obter_usuario_logado)):
    with Session(engine) as session:
        query = select(Tarefa).where(Tarefa.id == id, Tarefa.usuario_id == usuario.id)
        tarefa = session.exec(query).first()
        
        if tarefa:
            session.delete(tarefa)
            session.commit()
        
        tarefas, tem_mais, total_paginas, pagina = obter_tarefas_paginadas(session, usuario.id)
        
        return templates.TemplateResponse(request, "lista_tarefas.html", {
            "request": request, 
            "tarefas": tarefas,
            "pagina": pagina,
            "total_paginas": total_paginas,
            "tem_mais": tem_mais,
            "busca": "", "tipo_busca": "", "prioridade_busca": ""
        })
    

def obter_tarefas_paginadas(session: Session, usuario_id: int, busca: str = '', tipo_busca: str = '',
                             prioridade_busca: str = '', pagina: int = 1):
    query = select(Tarefa).where(Tarefa.usuario_id == usuario_id)
    
    if busca:
        query = query.where(Tarefa.titulo.contains(busca))
    if tipo_busca:
        query = query.where(Tarefa.tipo == tipo_busca)
    if prioridade_busca:
        query = query.where(Tarefa.prioridade == prioridade_busca)
        
    total_tarefas = len(session.exec(query).all())
    tarefas_por_pagina = 4
    total_paginas = max(1, (total_tarefas + tarefas_por_pagina - 1) // tarefas_por_pagina)
    
    if pagina > total_paginas: pagina = total_paginas
    if pagina < 1: pagina = 1
    
    offset = (pagina - 1) * tarefas_por_pagina
    tarefas_db = session.exec(query.offset(offset).limit(tarefas_por_pagina + 1)).all()
    
    tem_mais = len(tarefas_db) > tarefas_por_pagina
    tarefas = tarefas_db[:tarefas_por_pagina]
    
    return tarefas, tem_mais, total_paginas, pagina