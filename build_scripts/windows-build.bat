python -m pip install -U setuptools wheel pip mock
copy distutils.cfg c:\Python34\Lib\distutils\distutils.cfg
python -m pip install -i https://pypi.anaconda.org/carlkl/simple mingwpy
set USE_SDL2=1
set USE_GSTREAMER=1
python -m pip install cython docutils pygments pypiwin32 kivy.deps.sdl2 kivy.deps.glew kivy.deps.gstreamer kivy.deps.glew_dev kivy.deps.sdl2_dev kivy.deps.gstreamer_dev --extra-index-url https://kivy.org/downloads/packages/simple/

git clone file:///z/git/mpf-mc c:\mpf-mc
c:
cd /mpf-mc/mpf/mc/core/audio

python setup.py build_ext --inplace --compiler=mingw32
cd /mpf-mc
pip install .
python -m unittest discover mpf


IF EXIST "%PROGRAMFILES(X86)%" (GOTO 64BIT) ELSE (GOTO 32BIT)

:64BIT
python setup.py bdist_wheel  --dist-dir=%~dp0%/wheels --plat-name win_amd64
GOTO END

:32BIT
python setup.py bdist_wheel  --dist-dir=%~dp0%/wheels --plat-name win32
GOTO END

:END
