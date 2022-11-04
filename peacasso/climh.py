import os
import asyncio
import typer
from typing import List
from peacasso.ws.backend.appmhws import main

# from peacasso.web.backend.app import launch

app = typer.Typer()


@app.command()
def ws(
    scheme: str = "wss",
    host: str = "meaningful.noir.studio",
    port: int = 443,
    path: str = "/ws/generate/",
    token: str = os.environ.get("MH_BACKEND_TOKEN"),
    cuda_device: List[int] = [0],
    max_reconnect: int = 30,
):
    """
    Launch the peacasso websocket client.Pass in parameters scheme, host, port, path and cuda_device to override the default values.
    """
    asyncio.run(main(
        scheme=scheme,
        host=host,
        port=port,
        path=path,
        token=token,
        cuda_device=cuda_device,
        max_reconnect=max_reconnect,
    ))        
        

@app.command()
def list():
    print("list")


def run():
    app()


if __name__ == "__main__":
    app()
