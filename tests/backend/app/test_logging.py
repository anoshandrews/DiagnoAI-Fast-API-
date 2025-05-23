from backend.app.core.logging import logging

def test_logger_level():
    assert logger.level == 10  # 10 means DEBUG level