
del /F /Q /S %HOMEPATH%\AppData\Roaming\Kodi\addons\plugin.video.embycon
rmdir /Q /S %HOMEPATH%\AppData\Roaming\Kodi\addons\plugin.video.embycon

xcopy /Y addon.xml %HOMEPATH%\AppData\Roaming\Kodi\addons\plugin.video.embycon\
xcopy /Y default.py %HOMEPATH%\AppData\Roaming\Kodi\addons\plugin.video.embycon\
xcopy /Y fanart.jpg %HOMEPATH%\AppData\Roaming\Kodi\addons\plugin.video.embycon\
xcopy /Y icon.png %HOMEPATH%\AppData\Roaming\Kodi\addons\plugin.video.embycon\
xcopy /Y kodi.png %HOMEPATH%\AppData\Roaming\Kodi\addons\plugin.video.embycon\
xcopy /Y service.py %HOMEPATH%\AppData\Roaming\Kodi\addons\plugin.video.embycon\

xcopy /E /Y resources %HOMEPATH%\AppData\Roaming\Kodi\addons\plugin.video.embycon\resources\

cd "%programfiles%\Kodi"
kodi.exe
