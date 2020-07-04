
del /F /Q /S %HOMEPATH%\AppData\Roaming\Kodi\addons\plugin.video.jellycon
rmdir /Q /S %HOMEPATH%\AppData\Roaming\Kodi\addons\plugin.video.jellycon

xcopy /Y addon.xml %HOMEPATH%\AppData\Roaming\Kodi\addons\plugin.video.jellycon\
xcopy /Y default.py %HOMEPATH%\AppData\Roaming\Kodi\addons\plugin.video.jellycon\
xcopy /Y fanart.jpg %HOMEPATH%\AppData\Roaming\Kodi\addons\plugin.video.jellycon\
xcopy /Y icon.png %HOMEPATH%\AppData\Roaming\Kodi\addons\plugin.video.jellycon\
xcopy /Y kodi.png %HOMEPATH%\AppData\Roaming\Kodi\addons\plugin.video.jellycon\
xcopy /Y service.py %HOMEPATH%\AppData\Roaming\Kodi\addons\plugin.video.jellycon\

xcopy /E /Y resources %HOMEPATH%\AppData\Roaming\Kodi\addons\plugin.video.jellycon\resources\

cd "%programfiles%\Kodi"
kodi.exe
