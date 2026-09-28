#include <windows.h>
#include <shellapi.h>

// Lightweight print helper using Win32 API (no CRT needed)
void PrintToStream(DWORD stdHandleType, const char *format, ...) {
    HANDLE hStream = GetStdHandle(stdHandleType);
    if (hStream == NULL || hStream == INVALID_HANDLE_VALUE) return;

    char buffer[1024];
    va_list args;
    va_start(args, format);
    // wvsprintfA is a Win32 API in user32.lib that formats va_list without CRT
    int len = wvsprintfA(buffer, format, args);
    va_end(args);

    if (len > 0) {
        DWORD written;
        WriteFile(hStream, buffer, (DWORD)len, &written, NULL);
    }
}

#define print_out(fmt, ...) PrintToStream(STD_OUTPUT_HANDLE, fmt, __VA_ARGS__)
#define print_err(fmt, ...) PrintToStream(STD_ERROR_HANDLE, fmt, __VA_ARGS__)

// Define the function signature for Py_Main
typedef int (*Py_Main_t)(int argc, wchar_t **argv);

// Zero-CRT entry point
void mainCRTStartup(void) {
    // Attach to parent console so stdout/stderr print to the terminal if launched from CLI
    AttachConsole(ATTACH_PARENT_PROCESS);

    int argc = 0;
    LPWSTR *argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    int result = 1;

    // 1. Load the Python DLL
    HMODULE hPython = LoadLibraryA("python3.dll");
    if (!hPython) {
        DWORD errorCode = GetLastError();
        print_err("Failed to load python3.dll. GetLastError() = %lu\n", errorCode);
        
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
            print_err("Error Details: %s\n", msgBuffer);
            LocalFree(msgBuffer);
        }
        
        goto cleanup;
    }

    // 2. Resolve the Py_Main export
    Py_Main_t Py_Main = (Py_Main_t)GetProcAddress(hPython, "Py_Main");
    if (!Py_Main) {
        print_err("Failed to find Py_Main export\n");
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