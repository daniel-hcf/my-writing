import uvicorn

from .config import HOST, PORT


def main() -> None:
    uvicorn.run("my_writing.app:app", host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
