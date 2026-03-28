import sys
import logging
from loguru import logger


LOG_FORMAT = (
    "<green>{time:HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
    "{message}"
)


class InterceptHandler(logging.Handler):
    """Route standard library / uvicorn logs through loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(level: str = "DEBUG") -> None:
    logger.remove()
    logger.add(sys.stdout, format=LOG_FORMAT, level=level, colorize=True)

    # Route uvicorn and fastapi logs through loguru
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        log = logging.getLogger(name)
        log.handlers = [InterceptHandler()]
        log.propagate = False
