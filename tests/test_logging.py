import logging
import sys

from src.telemetry.logger import setup_logging


def test_application_logs_use_stderr_so_cli_stdout_can_remain_machine_readable():
    logger = logging.getLogger("ai_abyss")
    original_handlers = list(logger.handlers)
    try:
        logger.handlers.clear()
        configured = setup_logging("INFO")
        assert len(configured.handlers) == 1
        assert configured.handlers[0].stream is sys.stderr
    finally:
        logger.handlers.clear()
        logger.handlers.extend(original_handlers)
