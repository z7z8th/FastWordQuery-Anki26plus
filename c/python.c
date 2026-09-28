#include <windows.h>
#include <stdio.h>

// Define the function signature for Py_Main
typedef int (*Py_Main_t)(int argc, wchar_t **argv);

int wmain(int argc, wchar_t *argv[]) {
    // 1. Load the Python DLL (e.g., Python 3.11)
    HMODULE hPython = LoadLibraryA("python3.dll");
    if (!hPython) {
        // Capture the exact Windows error code
        DWORD errorCode = GetLastError();
        printf("Failed to load python3.dll. GetLastError() = %lu\n", errorCode);
        
        // Optional: Print the descriptive Windows error message string
        LPVOID msgBuffer;
        FormatMessageA(
            FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
            NULL,
            errorCode,
            MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
            (LPSTR)&msgBuffer,
            0, NULL
        );
        printf("Error Details: %s\n", (LPSTR)msgBuffer);
        LocalFree(msgBuffer);
        
        return 1;
    }

    // 2. Resolve the Py_Main export
    Py_Main_t Py_Main = (Py_Main_t)GetProcAddress(hPython, "Py_Main");
    if (!Py_Main) {
        printf("Failed to find Py_Main export\n");
        FreeLibrary(hPython);
        return 1;
    }

    // 3. Run Python's main handler with command-line arguments
    // (Note: Py_Main in modern Python takes wide character arguments)
    int result = Py_Main(argc, argv);

    FreeLibrary(hPython);
    return result;
}
