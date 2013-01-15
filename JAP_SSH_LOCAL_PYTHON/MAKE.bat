set SEVENZIP_HOME="C:\Program Files\7-Zip"
set PYINSTALLER_HOME="C:\pyinstaller-2.0"
set JAP_SSH_LOCAL_PYTHON_VERSION=2.0.0-SNAPSHOT-2
set JAP_SSH_LOCAL_PYTHON_WINDOWS_VERSION=2.0.0-SNAPSHOT-2
if exist MAKE rmdir MAKE /s /q
mkdir MAKE
cd MAKE
rem JAP_SSH_LOCAL_PYTHON
mkdir JAP_SSH_LOCAL_PYTHON-%JAP_SSH_LOCAL_PYTHON_VERSION%
cd JAP_SSH_LOCAL_PYTHON-%JAP_SSH_LOCAL_PYTHON_VERSION%
copy ..\..\JAP_SSH_LOCAL.bat JAP_SSH_LOCAL.bat
copy ..\..\JAP_SSH_LOCAL.json JAP_SSH_LOCAL.json
copy ..\..\JAP_SSH_LOCAL.py JAP_SSH_LOCAL.py
copy ..\..\KP KP
copy ..\..\KP.bat KP.bat
copy ..\..\KP.pub KP.pub
copy ..\..\README.txt README.txt
mkdir JAP
cd JAP
copy ..\..\..\JAP\__init__.py __init__.py
copy ..\..\..\JAP\JAP_LOCAL.py JAP_LOCAL.py
copy ..\..\..\JAP\TUNNEL.py TUNNEL.py
copy ..\..\..\JAP\JAP_SSH_LOCAL.py JAP_SSH_LOCAL.py
cd ..
cd ..
%SEVENZIP_HOME%\7z.exe a -tzip JAP_SSH_LOCAL_PYTHON-%JAP_SSH_LOCAL_PYTHON_VERSION%.zip JAP_SSH_LOCAL_PYTHON-%JAP_SSH_LOCAL_PYTHON_VERSION%
rem JAP_SSH_LOCAL_PYTHON_WINDOWS
mkdir PYINSTALLER
cd PYINSTALLER
python %PYINSTALLER_HOME%\pyinstaller.py -c -F ..\..\JAP_SSH_LOCAL.py
cd ..
mkdir JAP_SSH_LOCAL_PYTHON_WINDOWS-%JAP_SSH_LOCAL_PYTHON_WINDOWS_VERSION%
cd JAP_SSH_LOCAL_PYTHON_WINDOWS-%JAP_SSH_LOCAL_PYTHON_WINDOWS_VERSION%
copy ..\PYINSTALLER\dist\JAP_SSH_LOCAL.exe JAP_SSH_LOCAL.exe
copy ..\..\JAP_SSH_LOCAL_PYTHON_WINDOWS\JAP_SSH_LOCAL.bat JAP_SSH_LOCAL.bat
copy ..\..\JAP_SSH_LOCAL_PYTHON_WINDOWS\README.txt README.txt
copy ..\..\JAP_SSH_LOCAL.json JAP_SSH_LOCAL.json
copy ..\..\KP KP
copy ..\..\KP.bat KP.bat
copy ..\..\KP.pub KP.pub
cd ..
%SEVENZIP_HOME%\7z.exe a -tzip JAP_SSH_LOCAL_PYTHON_WINDOWS-%JAP_SSH_LOCAL_PYTHON_WINDOWS_VERSION%.zip JAP_SSH_LOCAL_PYTHON_WINDOWS-%JAP_SSH_LOCAL_PYTHON_WINDOWS_VERSION%
cd ..