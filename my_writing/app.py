import logging
import threading
import time
import webbrowser

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from .auth import require_auth
from .config import HOST, PORT, WEB_DIR
from .db import init_db
from .routers import ai_test, assignments, auth, config as config_router, stats, submissions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="my-writing", version="0.1.0")

    app.include_router(auth.router)

    protected = {"dependencies": [Depends(require_auth)]}
    app.include_router(config_router.router, **protected)
    app.include_router(ai_test.router, **protected)
    app.include_router(assignments.router, **protected)
    app.include_router(submissions.router, **protected)
    app.include_router(stats.router, **protected)

    if WEB_DIR.exists():
        app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    else:
        log.warning("web 目录不存在：%s", WEB_DIR)

    @app.on_event("startup")
    def _open_browser_async():
        def _open():
            time.sleep(0.5)
            try:
                webbrowser.open(f"http://{HOST}:{PORT}")
            except Exception as e:
                log.info("自动打开浏览器失败，请手动访问 http://%s:%s（%s）", HOST, PORT, e)

        threading.Thread(target=_open, daemon=True).start()

    return app


app = create_app()
