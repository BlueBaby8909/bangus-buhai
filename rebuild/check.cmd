@echo off
setlocal
pushd "%~dp0" || exit /b 1

set "CHECK_PYTHON=%~dp0backend\.venv\Scripts\python.exe"

set "CHECK_STEP=Python dependencies"
echo [%CHECK_STEP%]
"%CHECK_PYTHON%" -m pip check || goto failed

set "CHECK_STEP=Contract tests"
echo [%CHECK_STEP%]
"%CHECK_PYTHON%" -m unittest discover -s contracts\tests -v || goto failed

set "CHECK_STEP=Shared examples and schemas"
echo [%CHECK_STEP%]
"%CHECK_PYTHON%" -m contracts check || goto failed

set "CHECK_STEP=Backend smoke check"
echo [%CHECK_STEP%]
"%CHECK_PYTHON%" -c "from backend.main import app, health; expected = {'status': 'ok', 'service': 'bangus-buhai-rebuild'}; raise SystemExit(0 if callable(app) and health() == expected else 1)" || goto failed

set "CHECK_STEP=Database configuration isolation"
echo [%CHECK_STEP%]
"%CHECK_PYTHON%" -m unittest backend.tests.test_database_config -v || goto failed

set "CHECK_STEP=Offline account, registry, readings and MQTT tests"
echo [%CHECK_STEP%]
"%CHECK_PYTHON%" -m unittest discover -s backend\tests\unit -v || goto failed

set "CHECK_STEP=Frontend lint"
echo [%CHECK_STEP%]
cd /d "%~dp0frontend" || goto failed
call npm run lint || goto failed

set "CHECK_STEP=Frontend build"
set "CHECK_STEP=Frontend unit and component tests"
echo [%CHECK_STEP%]
call npm test || goto failed

set "CHECK_STEP=Frontend build"
echo [%CHECK_STEP%]
call npm run build || goto failed

echo All rebuild checks passed.
popd
exit /b 0

:failed
echo ERROR: %CHECK_STEP% failed.
popd
exit /b 1
