from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

templates = Jinja2Templates(directory=["Templates", "templates"])

@app.get("/home",response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(request, "index.html", {"pagina": "/home  /curtir"})

@app.get("/home/curtir", response_class=HTMLResponse)
async def pag2(request: Request):
    if (not "HX-Request" in request.headers):
        return templates.TemplateResponse(request, "index.html")
    return templates.TemplateResponse(request, "curtir.html")