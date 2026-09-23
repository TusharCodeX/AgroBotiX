@echo off
title AgriPath Rover Web Application
echo ========================================================
echo   Starting AgriPath Rover Web System on Port 8000...
echo ========================================================

rem Try anaconda python if in default location or system python
if exist "C:\Users\royde\anaconda3\envs\opencv\python.exe" (
    set PYTHON_EXE="C:\Users\royde\anaconda3\envs\opencv\python.exe"
) else (
    set PYTHON_EXE=python
)

echo Launching FastAPI + React UI at http://localhost:8000
%PYTHON_EXE% -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
