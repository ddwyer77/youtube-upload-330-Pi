import os
import logging
import logging.handlers
from pathlib import Path

def setup_logger(log_level=logging.INFO, log_file=None):
    """
    Configure the application logger.
    
    Args:
        log_level (int): Logging level (e.g., logging.INFO, logging.DEBUG).
        log_file (str): Path to the log file. If None, it will use 
                      ~/.youtube_shorts_uploader/logs/app.log
                      
    Returns:
        logging.Logger: Configured logger.
    """
    # Create root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if log_file is provided
    if log_file is None:
        home_dir = Path.home()
        log_dir = home_dir / ".youtube_shorts_uploader" / "logs"
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "app.log"
    else:
        log_file = Path(log_file)
        log_dir = log_file.parent
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create rotating file handler (10 MB max size, keep 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Add a filter to suppress noisy logs from third-party libraries
    class ThirdPartyFilter(logging.Filter):
        def filter(self, record):
            return not (
                record.name.startswith('googleapiclient') or
                record.name.startswith('urllib3') or
                record.name.startswith('google_auth_httplib2')
            ) or record.levelno >= logging.WARNING
    
    logging.getLogger().addFilter(ThirdPartyFilter())
    
    # Log startup info
    logger.info("Logger initialized")
    logger.info(f"Log file: {log_file}")
    
    return logger

def get_logger(name):
    """
    Get a logger with the specified name.
    
    Args:
        name (str): Logger name.
        
    Returns:
        logging.Logger: Logger instance.
    """
    return logging.getLogger(name)
