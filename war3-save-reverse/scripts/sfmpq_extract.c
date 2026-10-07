#define WINAPI __stdcall
#define CDECL __cdecl
#define GENERIC_WRITE 0x40000000u
#define CREATE_ALWAYS 2u
#define FILE_ATTRIBUTE_NORMAL 0x80u
#define INVALID_HANDLE_VALUE ((void *)-1)
#define NULL ((void *)0)

typedef unsigned int uint32_t;
typedef unsigned long long usize_t;
typedef void *HMODULE;
typedef void *HANDLE;
typedef uint32_t DWORD;
typedef int BOOL;

__declspec(dllimport) HMODULE WINAPI LoadLibraryA(const char *);
__declspec(dllimport) void *WINAPI GetProcAddress(HMODULE, const char *);
__declspec(dllimport) DWORD WINAPI GetLastError(void);
__declspec(dllimport) DWORD WINAPI GetEnvironmentVariableA(const char *, char *, DWORD);
__declspec(dllimport) HANDLE WINAPI GetProcessHeap(void);
__declspec(dllimport) void *WINAPI HeapAlloc(HANDLE, DWORD, size_t);
__declspec(dllimport) BOOL WINAPI HeapFree(HANDLE, DWORD, void *);
__declspec(dllimport) BOOL WINAPI CreateDirectoryA(const char *, void *);
__declspec(dllimport) HANDLE WINAPI CreateFileA(const char *, DWORD, DWORD, void *, DWORD, DWORD, HANDLE);
__declspec(dllimport) BOOL WINAPI WriteFile(HANDLE, const void *, DWORD, DWORD *, void *);
__declspec(dllimport) BOOL WINAPI CloseHandle(HANDLE);
int CDECL printf(const char *, ...);
int CDECL fprintf(void *, const char *, ...);
void *CDECL __acrt_iob_func(unsigned int);
int CDECL _snprintf(char *, usize_t, const char *, ...);

#define stderr (__acrt_iob_func(2))

typedef int(WINAPI *SFileOpenArchiveFn)(const char *, uint32_t, uint32_t, void **);
typedef int(WINAPI *SFileOpenFileExFn)(void *, const char *, uint32_t, void **);
typedef uint32_t(WINAPI *SFileGetFileSizeFn)(void *, uint32_t *);
typedef int(WINAPI *SFileReadFileFn)(void *, void *, uint32_t, uint32_t *, void *);
typedef int(WINAPI *SFileCloseFileFn)(void *);
typedef int(WINAPI *SFileCloseArchiveFn)(void *);

static HMODULE load_sfmpq(void) {
    const char *fallbacks[] = {
        "sfmpq.dll",
        "C:\\Program Files\\Warcraft III\\_retail_\\x86_64\\JassHelper\\sfmpq.dll",
        NULL,
    };
    char env[1024];
    DWORD n = GetEnvironmentVariableA("SFMPQ_DLL", env, sizeof(env));
    if (n > 0 && n < sizeof(env)) {
        HMODULE dll = LoadLibraryA(env);
        if (dll) return dll;
    }
    for (int i = 0; fallbacks[i]; i++) {
        HMODULE dll = LoadLibraryA(fallbacks[i]);
        if (dll) return dll;
    }
    return NULL;
}

static void safe_name(const char *in, char *out, usize_t cap) {
    usize_t j = 0;
    for (usize_t i = 0; in[i] && j + 1 < cap; i++) {
        char c = in[i];
        if (c == '\\' || c == '/' || c == ':' || c == '*' || c == '?' || c == '"' || c == '<' || c == '>' || c == '|') c = '_';
        out[j++] = c;
    }
    out[j] = 0;
}

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "Usage: sfmpq_extract <archive> <outdir> <file> [file...]\n");
        return 2;
    }

    HMODULE dll = load_sfmpq();
    if (!dll) {
        fprintf(stderr, "LoadLibrary sfmpq.dll failed: %lu\n", GetLastError());
        return 1;
    }

    SFileOpenArchiveFn SFileOpenArchive = (SFileOpenArchiveFn)GetProcAddress(dll, "SFileOpenArchive");
    SFileOpenFileExFn SFileOpenFileEx = (SFileOpenFileExFn)GetProcAddress(dll, "SFileOpenFileEx");
    SFileGetFileSizeFn SFileGetFileSize = (SFileGetFileSizeFn)GetProcAddress(dll, "SFileGetFileSize");
    SFileReadFileFn SFileReadFile = (SFileReadFileFn)GetProcAddress(dll, "SFileReadFile");
    SFileCloseFileFn SFileCloseFile = (SFileCloseFileFn)GetProcAddress(dll, "SFileCloseFile");
    SFileCloseArchiveFn SFileCloseArchive = (SFileCloseArchiveFn)GetProcAddress(dll, "SFileCloseArchive");
    if (!SFileOpenArchive || !SFileOpenFileEx || !SFileGetFileSize || !SFileReadFile || !SFileCloseFile || !SFileCloseArchive) {
        fprintf(stderr, "GetProcAddress failed\n");
        return 1;
    }

    void *archive = NULL;
    if (!SFileOpenArchive(argv[1], 0, 0, &archive)) {
        fprintf(stderr, "SFileOpenArchive failed\n");
        return 1;
    }

    CreateDirectoryA(argv[2], NULL);
    for (int i = 3; i < argc; i++) {
        void *file = NULL;
        if (!SFileOpenFileEx(archive, argv[i], 0, &file)) {
            printf("MISS %s\n", argv[i]);
            continue;
        }
        uint32_t high = 0;
        uint32_t low = SFileGetFileSize(file, &high);
        if (high != 0) {
            printf("SKIP_BIG %s\n", argv[i]);
            SFileCloseFile(file);
            continue;
        }
        unsigned char *buf = (unsigned char *)HeapAlloc(GetProcessHeap(), 0, low);
        uint32_t got = 0;
        if (!buf || !SFileReadFile(file, buf, low, &got, NULL) || got != low) {
            printf("READ_FAIL %s\n", argv[i]);
            if (buf) HeapFree(GetProcessHeap(), 0, buf);
            SFileCloseFile(file);
            continue;
        }
        char name[512];
        safe_name(argv[i], name, sizeof(name));
        char out[1024];
        _snprintf(out, sizeof(out), "%s\\%s", argv[2], name);
        HANDLE h = CreateFileA(out, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
        if (h == INVALID_HANDLE_VALUE) {
            printf("WRITE_FAIL %s\n", argv[i]);
        } else {
            DWORD written = 0;
            WriteFile(h, buf, low, &written, NULL);
            CloseHandle(h);
            printf("OK %s -> %s %u\n", argv[i], out, low);
        }
        HeapFree(GetProcessHeap(), 0, buf);
        SFileCloseFile(file);
    }
    SFileCloseArchive(archive);
    return 0;
}
