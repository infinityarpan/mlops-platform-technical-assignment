from pathlib import Path


def mlflow_sqlite_uri(directory: Path) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{directory.resolve().as_posix()}/mlflow.db"
