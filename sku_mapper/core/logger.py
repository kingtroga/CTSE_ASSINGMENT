import logging
from pathlib import Path
from ..utils.constants import Config

class WMSLogger:
    """Centralized logging system for WMS operations"""
    
    def __init__(self):
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Setup logging for mapping process"""
        # Create logs directory
        Config.LOGS_DIR.mkdir(exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(Config.LOGS_DIR / 'sku_mapping.log'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def log_process(self, component: str, action: str, message: str):
        """Log process with structured format"""
        log_message = f"{component} | {action} | {message}"
        self.logger.info(log_message)
        print(log_message)  # Also print to console
