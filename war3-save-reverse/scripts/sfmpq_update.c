#define WINAPI __stdcall
#define CDECL __cdecl
#define NULL ((void *)0)

typedef unsigned int uint32_t;
typedef void *HMODULE;
typedef unsigned int DWORD;

__declspec(dllimport) HMODULE WINAPI LoadLibraryA(const char *);
__declspec(dllimport) void *WINAPI GetProcAddress(HMODULE, const char *);
__declspec(dllimport) DWORD WINAPI GetLastError(void);
__declspec(dllimport) DWORD WINAPI GetEnvironmentVariableA(const char *, char *, DWORD);
int CDECL printf(const char *, ...);
int CDECL fprintf(void *, const char *, ...);
void *CDECL __acrt_iob_func(unsigned int);

#define stderr (__acrt_iob_func(2))

typedef void *(WINAPI *MpqOpenArchiveForUpdateFn)(const char *, uint32_t, uint32_t);
typedef int(WINAPI *MpqCloseUpdatedArchiveFn)(void *, uint32_t);
typedef int(WINAPI *MpqAddFileToArchiveFn)(void *, const char *, const char *, uint32_t);
typedef int(WINAPI *MpqCompactArchiveFn)(void *);

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

static int add_one(MpqAddFileToArchiveFn MpqAddFileToArchive, void *archive, const char *source, const char *dest) {
    const uint32_t MAFA_REPLACE_EXISTING = 0x00000001;
    if (!MpqAddFileToArchive(archive, source, dest, MAFA_REPLACE_EXISTING)) {
        fprintf(stderr, "MpqAddFileToArchive failed: %s -> %s\n", source, dest);
        return 1;
    }
    printf("OK %s -> %s\n", source, dest);
    return 0;
}

int main(int argc, char **argv) {
    const uint32_t MOAU_OPEN_EXISTING = 0x00000004;
    int status = 0;

    if (argc < 4 || ((argc - 2) % 2) != 0) {
        fprintf(stderr, "Usage: sfmpq_update <archive> <source> <dest> [source dest...]\n");
        return 2;
    }

    HMODULE dll = load_sfmpq();
    if (!dll) {
        fprintf(stderr, "LoadLibrary sfmpq.dll failed: %lu\n", GetLastError());
        return 1;
    }

    MpqOpenArchiveForUpdateFn MpqOpenArchiveForUpdate =
        (MpqOpenArchiveForUpdateFn)GetProcAddress(dll, "MpqOpenArchiveForUpdate");
    MpqCloseUpdatedArchiveFn MpqCloseUpdatedArchive =
        (MpqCloseUpdatedArchiveFn)GetProcAddress(dll, "MpqCloseUpdatedArchive");
    MpqAddFileToArchiveFn MpqAddFileToArchive =
        (MpqAddFileToArchiveFn)GetProcAddress(dll, "MpqAddFileToArchive");
    MpqCompactArchiveFn MpqCompactArchive =
        (MpqCompactArchiveFn)GetProcAddress(dll, "MpqCompactArchive");
    if (!MpqOpenArchiveForUpdate || !MpqCloseUpdatedArchive || !MpqAddFileToArchive || !MpqCompactArchive) {
        fprintf(stderr, "GetProcAddress failed\n");
        return 1;
    }

    void *archive = MpqOpenArchiveForUpdate(argv[1], MOAU_OPEN_EXISTING, 0);
    if (!archive) {
        fprintf(stderr, "MpqOpenArchiveForUpdate failed: %s\n", argv[1]);
        return 1;
    }

    for (int i = 2; i + 1 < argc; i += 2) {
        status |= add_one(MpqAddFileToArchive, archive, argv[i], argv[i + 1]);
    }

    if (!MpqCompactArchive(archive)) {
        fprintf(stderr, "MpqCompactArchive failed\n");
        status = 1;
    }
    if (!MpqCloseUpdatedArchive(archive, 0)) {
        fprintf(stderr, "MpqCloseUpdatedArchive failed\n");
        status = 1;
    }
    return status;
}
