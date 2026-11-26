@echo off
chcp 65001 >nul
title 腰衡 . 动作评估（回放演示）
cd /d "%~dp0"
echo.
echo   正在启动演示页...
echo.
python serve.py --port 9101
if errorlevel 1 (
  echo.
  echo   [失败] 需要本机安装 Python 3。
  echo   如果只是想看看页面，直接双击 index.html 也可以。
  pause
)
