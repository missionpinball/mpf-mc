:: Tests installing mpf-mc from the wheel. Assumes a blank system with nothing installed (except Python) to simulate a
:: fresh environment. Note that if this version of mpf-mc requires a version of mpf that is not in PyPI, then you also
:: need to have that version of mpf installed.

cd wheels

IF EXIST "%PROGRAMFILES(X86)%" (GOTO 64BIT) ELSE (GOTO 32BIT)

:64BIT
FOR /F "delims=|" %%I IN ('dir "mpf_mc-*64.whl" /b /o:-n ') DO SET mpf-wheel=%%I
GOTO END

:32BIT
FOR /F "delims=|" %%I IN ('dir "mpf_mc-*32.whl" /b /o:-n ') DO SET mpf-wheel=%%I
GOTO END

:END
pip install %mpf-wheel%
pip install mock
python -m unittest discover mpf
