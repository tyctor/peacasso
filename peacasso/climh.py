import typer
import uvicorn

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
def list():
    print("list")


def run():
    app()


if __name__ == "__main__":
    app()
