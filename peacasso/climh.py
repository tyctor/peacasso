import os
import asyncio
import typer
import uvicorn
from peacasso.ws.backend.appmhws import main

# from peacasso.web.backend.app import launch

app = typer.Typer()


@app.command()
def ui(
    host: str = "127.0.0.1", port: int = 8081, workers: int = 1, reload: bool = True
):
    """
    Launch the peacasso UI.Pass in parameters host, port, workers, and reload to override the default values.
    """
    uvicorn.run(
        "peacasso.web.backend.appmh:app",
        host=host,
        port=port,
        workers=workers,
        reload=reload,
    )


@app.command()
def ws(
    scheme: str = "ws",
    host: str = "meaningful.noir.studio",
    port: int = 8000,
    path: str = "/ws/generate/",
    token: str = os.environ.get("MH_BACKEND_TOKEN") 
):
    """
    Launch the peacasso websocket client.Pass in parameters scheme, host, port and path to override the default values.
    """
    asyncio.run(main(
        scheme=scheme,
        host=host,
        port=port,
        path=path,
        token=token
    ))        
        

@app.command()
def list():
    print("list")


def run():
    app()


if __name__ == "__main__":
    app()
