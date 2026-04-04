from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel

class Usuario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    bio: str
    curso: str
    
    tarefas: List["Tarefa"] = Relationship(back_populates="usuario")

class Tarefa(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    titulo: str
    tipo: str
    prioridade: str
    usuario_id: int = Field(foreign_key="usuario.id")
    
    usuario: Optional["Usuario"] = Relationship(back_populates="tarefas")