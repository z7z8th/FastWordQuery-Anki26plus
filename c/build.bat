
CALL "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"

rem cl /nologo /O2 /Oi /Gy /W3 /D "NDEBUG" python.c /Fe:python3.exe /link /OPT:REF /OPT:ICF

cl /nologo /O1 /Gy python.c /Fe:python3.exe /link /NODEFAULTLIB kernel32.lib user32.lib shell32.lib /SUBSYSTEM:CONSOLE
