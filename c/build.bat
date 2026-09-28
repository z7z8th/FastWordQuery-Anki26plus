
CALL "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"

cl /nologo /O2 /Oi /Gy /W3 /D "NDEBUG" python.c /Fe:python3.exe /link /OPT:REF /OPT:ICF

