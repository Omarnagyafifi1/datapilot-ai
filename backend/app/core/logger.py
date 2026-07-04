import logging
import sys
import os

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance with production formatting."""
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if get_logger is called multiple times on the same name
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO if os.getenv("DEBUG", "false").lower() != "true" else logging.DEBUG)
    
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(name)s (%(filename)s:%(lineno)d): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Stream handler (stdout)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Prevent propagation to the root logger to avoid duplicated logs
    logger.propagate = False
    
    return logger
