import logging
import sys
from backend.app.core.config import settings

def setup_logging():
    """
    Configure logging for the application.
    """
    # Determine log level
    log_level = logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO
    
    # Basic configuration
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific levels for libraries
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    
    # Enable SQL query logging in development
    if settings.ENVIRONMENT == "development":
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    else:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    # Project specific loggers
    logging.getLogger("backend").setLevel(log_level)
    
    logger = logging.getLogger("backend.core.logging")
    logger.info(f"Logging setup complete. Level: {logging.getLevelName(log_level)}")

# Call setup on import
setup_logging()