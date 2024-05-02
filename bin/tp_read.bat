@echo off
rem %~dp0 is the directory containing the current batch file.
rem This lets the script use the working directory of the shell
rem when it's run.
python "%~dp0\tp_read.py" %*