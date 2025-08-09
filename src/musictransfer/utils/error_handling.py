import logging
import functools
import time
from typing import Any, Callable, TypeVar
from requests.exceptions import RequestException

# Define generic type variable
T = TypeVar('T')

class RateLimiter:
    """
    API rate limiter
    """
    
    def __init__(self, max_calls: int = 10, time_window: float = 1.0):
        """
        Initialize rate limiter
        
        Args:
            max_calls: Maximum number of calls in the time window
            time_window: Time window (seconds)
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    def acquire(self) -> None:
        """
        Acquire call permission, wait if necessary
        """
        now = time.time()
        
        # Clean up expired call records
        self.calls = [call_time for call_time in self.calls 
                     if now - call_time < self.time_window]
        
        # If limit is reached, wait
        if len(self.calls) >= self.max_calls:
            sleep_time = self.time_window - (now - self.calls[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        # Record current call
        self.calls.append(now)

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, 
                      max_delay: float = 60.0, exceptions: tuple = (Exception,)):
    """
    Retry decorator with exponential backoff
    
    Args:
        max_retries: Maximum number of retries
        base_delay: Base delay time (seconds)
        max_delay: Maximum delay time (seconds)
        exceptions: Tuple of exception types to retry
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            logger = logging.getLogger(__name__)
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {str(e)}")
                        raise
                    
                    # Calculate delay time (exponential backoff)
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    
                    logger.warning(
                        f"Function {func.__name__} call {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {delay} seconds..."
                    )
                    
                    time.sleep(delay)
            
            # This line will not be executed, but needed for type checking
            raise RuntimeError("Unexpected code path")
        
        return wrapper
    return decorator

def setup_logging(log_file: str = "music_transfer.log", log_level: int = logging.INFO) -> None:
    """
    Setup logging configuration
    
    Args:
        log_file: Log file path
        log_level: Log level
    """
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Create file handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

class APIError(Exception):
    """
    API call exception class
    """
    
    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

class AuthenticationError(APIError):
    """
    Authentication exception class
    """
    pass

class RateLimitError(APIError):
    """
    Rate limit exception class
    """
    pass

def handle_api_errors(func: Callable[..., T]) -> Callable[..., T]:
    """
    API error handling decorator
    
    Args:
        func: Decorated function
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        logger = logging.getLogger(__name__)
        
        try:
            return func(*args, **kwargs)
        except RequestException as e:
            logger.error(f"Network request error: {str(e)}")
            raise APIError(f"Network request failed: {str(e)}") from e
        except Exception as e:
            # Check if it's a specific API error
            if "401" in str(e) or "Unauthorized" in str(e):
                raise AuthenticationError("Authentication failed, please check authentication information") from e
            elif "429" in str(e) or "rate limit" in str(e).lower():
                raise RateLimitError("API call frequency is too high, please try again later") from e
            else:
                logger.error(f"Unexpected error: {str(e)}")
                raise APIError(f"Operation failed: {str(e)}") from e
    
    return wrapper