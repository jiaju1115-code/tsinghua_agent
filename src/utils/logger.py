import logging
from utils.security import redact

def get_logger(path):
    logger=logging.getLogger("reviewer");logger.setLevel(logging.INFO);logger.handlers.clear()
    handler=logging.FileHandler(path,encoding="utf-8");handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"));logger.addHandler(handler)
    return logger

def safe_log(logger,level,message):getattr(logger,level)(redact(message))

