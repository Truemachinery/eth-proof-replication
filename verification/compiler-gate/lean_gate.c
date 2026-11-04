#define _DARWIN_C_SOURCE
#include <CommonCrypto/CommonDigest.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#include "gate_config.h"

/* Mac-local admission wrapper. It never edits compiler arguments or outputs.
 * A POSIX record lock is retained across exec by this same process/PID. */
static void die(const char *message) {
    fprintf(stderr, "lean admission gate: %s (%s)\n", message, strerror(errno));
    exit(125);
}

static double now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) die("clock_gettime");
    return (double)t.tv_sec + (double)t.tv_nsec / 1e9;
}

static void json_string(FILE *f, const char *s) {
    fputc('"', f);
    for (const unsigned char *p = (const unsigned char *)s; *p; ++p) {
        if (*p == '"' || *p == '\\') fprintf(f, "\\%c", *p);
        else if (*p < 32) fprintf(f, "\\u%04x", *p);
        else fputc(*p, f);
    }
    fputc('"', f);
}

static void compiler_identity(void) {
    unsigned char block[65536], digest[CC_SHA256_DIGEST_LENGTH];
    CC_SHA256_CTX context;
    char hex[CC_SHA256_DIGEST_LENGTH * 2 + 1];
    int fd = open(REAL_COMPILER, O_RDONLY | O_NOFOLLOW);
    if (fd < 0) die("opening exact real compiler");
    if (!CC_SHA256_Init(&context)) die("initializing compiler SHA-256");
    for (;;) {
        ssize_t count = read(fd, block, sizeof block);
        if (count < 0) { if (errno == EINTR) continue; die("reading real compiler"); }
        if (!count) break;
        if (!CC_SHA256_Update(&context, block, (CC_LONG)count)) die("hashing compiler");
    }
    if (close(fd)) die("closing compiler identity input");
    if (!CC_SHA256_Final(digest, &context)) die("finishing compiler SHA-256");
    for (size_t i = 0; i < sizeof digest; ++i) sprintf(hex + 2 * i, "%02x", digest[i]);
    hex[sizeof hex - 1] = 0;
    if (strcmp(hex, EXPECTED_COMPILER_SHA)) {
        errno = EINVAL;
        die("real compiler SHA-256 differs from pinned executable");
    }
}

static void log_event(const char *event, int slot, int slots, double waited, int argc, char **argv) {
    int fd = open(LOG_PATH, O_WRONLY | O_CREAT | O_APPEND | O_NOFOLLOW, 0600);
    if (fd < 0) die("opening admission journal");
    if (flock(fd, LOCK_EX)) die("locking admission journal");
    FILE *f = fdopen(fd, "a");
    if (!f) die("opening admission journal stream");
    fprintf(f, "{\"schema\":\"lean-admission/1\",\"event\":");
    json_string(f, event);
    fprintf(f, ",\"pid\":%ld,\"slot\":%d,\"configured_slots\":%d,\"monotonic_seconds\":%.9f,\"wait_seconds\":%.9f,\"compiler_sha256\":", (long)getpid(), slot, slots, now(), waited);
    json_string(f, EXPECTED_COMPILER_SHA);
    fprintf(f, ",\"real_compiler\":"); json_string(f, REAL_COMPILER);
    fprintf(f, ",\"argv\":[");
    for (int i = 0; i < argc; ++i) { if (i) fputc(',', f); json_string(f, argv[i]); }
    fprintf(f, "]}\n");
    if (fflush(f) || fsync(fd)) die("persisting admission journal");
    if (flock(fd, LOCK_UN)) die("unlocking admission journal");
    if (fclose(f)) die("closing admission journal");
}

#ifdef GATE_STATUS_EXEC
int main(void) {
    int fd = open(LOCK_PATH, O_RDWR | O_CREAT | O_NOFOLLOW, 0600);
    if (fd < 0) die("opening status lock file");
    printf("{\"slots\":[");
    for (int i = 0; i < 4; ++i) {
        struct flock lock = {0};
        lock.l_type = F_WRLCK; lock.l_whence = SEEK_SET; lock.l_start = i; lock.l_len = 1;
        if (fcntl(fd, F_GETLK, &lock)) die("querying admission slot");
        if (i) putchar(',');
        printf("{\"slot\":%d,\"pid\":%ld}", i, lock.l_type == F_UNLCK ? 0L : (long)lock.l_pid);
    }
    printf("]}\n");
    if (close(fd)) die("closing status lock file");
    return 0;
}
#else
int main(int argc, char **argv) {
    compiler_identity();
    /* Metadata must not wait behind long compilation jobs during Lake setup. */
    if (argc == 2 && (!strcmp(argv[1], "--version") || !strcmp(argv[1], "--githash") ||
                     !strcmp(argv[1], "--print-prefix") || !strcmp(argv[1], "--print-libdir") ||
                     !strcmp(argv[1], "--help") || !strcmp(argv[1], "-h"))) {
        execv(REAL_COMPILER, argv);
        die("executing compiler metadata query");
    }
    int slots = 2;
    const char *slot_env = getenv("MINING_LAB_LEAN_SLOTS");
    if (slot_env) {
        char *end = NULL; long parsed = strtol(slot_env, &end, 10);
        if (!*slot_env || *end || parsed < 2 || parsed > 4) {
            errno = EINVAL; die("MINING_LAB_LEAN_SLOTS must be 2, 3 or 4");
        }
        slots = (int)parsed;
    }
    int fd = open(LOCK_PATH, O_RDWR | O_CREAT | O_NOFOLLOW, 0600);
    if (fd < 0) die("opening slot lock file");
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0 || fcntl(fd, F_SETFD, flags & ~FD_CLOEXEC)) die("retaining slot across exec");
    double started = now();
    int slot = -1, waiting_logged = 0;
    while (slot < 0) {
        for (int i = 0; i < slots; ++i) {
            struct flock lock = {0};
            lock.l_type = F_WRLCK; lock.l_whence = SEEK_SET; lock.l_start = i; lock.l_len = 1;
            if (!fcntl(fd, F_SETLK, &lock)) { slot = i; break; }
            if (errno != EACCES && errno != EAGAIN && errno != EINTR) die("acquiring compiler slot");
        }
        if (slot < 0) {
            if (!waiting_logged) { log_event("waiting", -1, slots, now() - started, argc, argv); waiting_logged = 1; }
            struct timespec pause = {0, 20000000};
            nanosleep(&pause, NULL);
        }
    }
    compiler_identity();
    log_event("admitted", slot, slots, now() - started, argc, argv);
    /* No fork: the lock-owning PID becomes the unchanged pinned compiler.
     * argv (including argv[0]) and stdin/stdout/stderr are forwarded unchanged. */
    execv(REAL_COMPILER, argv);
    die("executing pinned compiler");
}
#endif
