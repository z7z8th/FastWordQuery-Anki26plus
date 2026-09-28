#include <windows.h>
#include <shellapi.h> // Required for CommandLineToArgvW

#undef printf
#define printf(...) ((void)0)

// Define the function signature for Py_Main
typedef int (*Py_Main_t)(int argc, wchar_t **argv);

// Zero-CRT entry point bypassing standard startup stubs
void mainCRTStartup(void) {
    int argc = 0;
    LPWSTR *argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    
    int result = 1;

    // 1. Load the Python DLL (e.g., Python 3.11 / generic python3.dll)
    HMODULE hPython = LoadLibraryA("python3.dll");
    if (!hPython) {
        // Capture the exact Windows error code
        DWORD errorCode = GetLastError();
        
        // Printf is safely stubbed out, but error code is captured if needed
        LPSTR msgBuffer = NULL;
        FormatMessageA(
            FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
            NULL,
            errorCode,
            MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
            (LPSTR)&msgBuffer,
            0, NULL
        );
        
        if (msgBuffer) {
            LocalFree(msgBuffer);
        }
        
        goto cleanup;
    }

    // 2. Resolve the Py_Main export
    Py_Main_t Py_Main = (Py_Main_t)GetProcAddress(hPython, "Py_Main");
    if (!Py_Main) {
        FreeLibrary(hPython);
        goto cleanup;
    }

    // 3. Run Python's main handler with command-line arguments
    result = Py_Main(argc, argv);

    FreeLibrary(hPython);

cleanup:
    if (argv) {
        LocalFree(argv);
    }
    ExitProcess(result);
}