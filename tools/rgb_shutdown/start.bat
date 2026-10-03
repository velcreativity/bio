@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist config.json (
    copy config.example.json config.json >nul
    echo.
    echo [안내] config.json 파일을 새로 만들었습니다.
    echo        메모장으로 config.json 을 열어 색과 위치를 수정하세요. (README.md 참고)
    echo.
)

python rgb_shutdown.py %*
if errorlevel 9009 (
    echo.
    echo [오류] python 을 찾을 수 없습니다. Python 설치 시 "Add to PATH" 를 체크했는지 확인하세요.
)

echo.
pause
