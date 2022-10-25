import os
import asyncio
import typer
import uvicorn
from peacasso.ws.backend.appmhws import main

# from peacasso.web.backend.app import launch

app = typer.Typer()


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
