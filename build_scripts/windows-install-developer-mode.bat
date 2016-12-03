python -m pip install -U setuptools wheel pip mock --retries 20 --timeout 60

pip install -e ../../mpf

copy distutils.cfg c:\Python34\Lib\distutils\distutils.cfg
python -m pip install -i https://pypi.anaconda.org/carlkl/simple mingwpy
set USE_SDL2=1
set USE_GSTREAMER=1
python -m pip install cython==0.24.1 docutils pygments pypiwin32 kivy.deps.sdl2 kivy.deps.glew kivy.deps.gstreamer kivy.deps.glew_dev kivy.deps.sdl2_dev kivy.deps.gstreamer_dev --extra-index-url https://kivy.org/downloads/packages/simple/ --retries 20 --timeout 60

pip install  -e ..

