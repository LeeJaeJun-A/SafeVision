import logging
import os
from datetime import datetime

def setup_logging():
    """로깅 시스템 설정"""
    # 로그 디렉토리 생성
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # 현재 시간으로 로그 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"analysis_{timestamp}.log")

    # 루트 로거 설정 (모든 로거에 적용)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 기존 핸들러 제거 (중복 방지)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 파일 핸들러 (상세 로그)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    # 콘솔 핸들러 (요약 로그)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)

    # 포맷터 설정
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 핸들러 추가
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # smart_safety 메인 로거 설정
    main_logger = logging.getLogger('smart_safety')
    main_logger.setLevel(logging.INFO)

    # 규칙 로거들 설정
    rule_loggers = [
        'fall_detection_rule',
        'collision_risk_rule',
        'speed_over_rule'
    ]
    
    for rule_logger_name in rule_loggers:
        rule_logger = logging.getLogger(rule_logger_name)
        rule_logger.setLevel(logging.INFO)
        # 부모 로거로부터 상속받도록 설정
        rule_logger.propagate = True

    return main_logger, log_file

def get_logger(name):
    """특정 모듈용 로거 반환"""
    return logging.getLogger(f'smart_safety.{name}')
