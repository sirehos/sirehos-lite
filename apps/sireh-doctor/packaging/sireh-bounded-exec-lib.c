
#define _POSIX_C_SOURCE 200809L

#include "sireh-bounded-exec.h"

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static int64_t monotonic_ms(void)
{
    struct timespec now;

    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0)
        return -1;

    return (int64_t)now.tv_sec * 1000 +
           now.tv_nsec / 1000000;
}

static void terminate_group(pid_t child)
{
    if (child > 0) {
        (void)kill(-child, SIGKILL);
        (void)kill(child, SIGKILL);
    }
}

static int reap_child(pid_t child, int *status)
{
    for (;;) {
        if (waitpid(child, status, 0) == child)
            return 0;

        if (errno != EINTR)
            return -1;
    }
}

static int sireh_exec_internal(
    const char *const argv[],
    int approved_fd,
    size_t max_output,
    unsigned int timeout_ms,
    struct sireh_exec_output *output
)
{
    if (output == NULL)
        return SIREH_EXEC_ERROR;

    output->data = NULL;
    output->length = 0;
    output->child_exit_code = -1;

    if (argv == NULL || argv[0] == NULL ||
        argv[0][0] != '/' ||
        approved_fd < -1 ||
        max_output == 0 ||
        max_output > 2U * 1024U * 1024U ||
        timeout_ms == 0 ||
        timeout_ms > 60000U)
        return SIREH_EXEC_ERROR;

    int pipefd[2];

    if (pipe(pipefd) != 0)
        return SIREH_EXEC_ERROR;

    int flags = fcntl(pipefd[0], F_GETFL);

    if (flags < 0 ||
        fcntl(pipefd[0], F_SETFL, flags | O_NONBLOCK) != 0) {
        close(pipefd[0]);
        close(pipefd[1]);
        return SIREH_EXEC_ERROR;
    }

    unsigned char *buffer = malloc(max_output);

    if (buffer == NULL) {
        close(pipefd[0]);
        close(pipefd[1]);
        return SIREH_EXEC_ERROR;
    }

    int64_t start = monotonic_ms();

    if (start < 0) {
        free(buffer);
        close(pipefd[0]);
        close(pipefd[1]);
        return SIREH_EXEC_ERROR;
    }

    pid_t child = fork();

    if (child < 0) {
        free(buffer);
        close(pipefd[0]);
        close(pipefd[1]);
        return SIREH_EXEC_ERROR;
    }

    if (child == 0) {
        if (setpgid(0, 0) != 0)
            _exit(70);

        close(pipefd[0]);

        if (dup2(pipefd[1], STDOUT_FILENO) < 0)
            _exit(70);

        close(pipefd[1]);

        /*
         * Preserve only the explicitly approved descriptor.
         * The parent retains ownership of its original fd.
         */
        if (approved_fd >= 0) {
            if (dup2(approved_fd, SIREH_EXEC_DEVICE_FD) < 0)
                _exit(70);

            int descriptor_flags =
                fcntl(SIREH_EXEC_DEVICE_FD, F_GETFD);

            if (descriptor_flags < 0 ||
                fcntl(SIREH_EXEC_DEVICE_FD, F_SETFD,
                      descriptor_flags & ~FD_CLOEXEC) < 0)
                _exit(70);
        }

        /*
         * Do not inherit arbitrary parent descriptors.
         * This is a development-stage isolation measure.
         */
        long limit = sysconf(_SC_OPEN_MAX);

        if (limit < 0 || limit > 65536)
            limit = 65536;

        for (int fd = 3; fd < limit; ++fd) {
            if (approved_fd >= 0 && fd == SIREH_EXEC_DEVICE_FD)
                continue;
            close(fd);
        }

        int nullfd = open("/dev/null", O_RDONLY);

        if (nullfd < 0)
            _exit(70);

        if (dup2(nullfd, STDIN_FILENO) < 0)
            _exit(70);

        if (nullfd > STDERR_FILENO)
            close(nullfd);

        /*
         * Explicit minimal environment.
         * Never inherit the invoking user's environment.
         */
        char *const clean_env[] = {
            "PATH=/usr/sbin:/usr/bin:/sbin:/bin",
            "LANG=C",
            "LC_ALL=C",
            NULL
        };

        execve(argv[0], (char *const *)argv, clean_env);
        _exit(70);
    }

    close(pipefd[1]);

    if (setpgid(child, child) != 0 &&
        errno != EACCES && errno != ESRCH) {
        terminate_group(child);
        close(pipefd[0]);
        int status;
        (void)reap_child(child, &status);
        free(buffer);
        return SIREH_EXEC_ERROR;
    }

    size_t used = 0;
    int result = SIREH_EXEC_OK;

    for (;;) {
        int64_t now = monotonic_ms();

        if (now < 0) {
            result = SIREH_EXEC_ERROR;
            break;
        }

        int64_t remaining = (int64_t)timeout_ms - (now - start);

        if (remaining <= 0) {
            result = SIREH_EXEC_TIMEOUT;
            break;
        }

        struct pollfd descriptor = {
            .fd = pipefd[0],
            .events = POLLIN | POLLHUP
        };

        int ready = poll(&descriptor, 1, (int)remaining);

        if (ready < 0) {
            if (errno == EINTR)
                continue;

            result = SIREH_EXEC_ERROR;
            break;
        }

        if (ready == 0) {
            result = SIREH_EXEC_TIMEOUT;
            break;
        }

        unsigned char chunk[4096];
        ssize_t count = read(pipefd[0], chunk, sizeof(chunk));

        if (count < 0) {
            if (errno == EINTR || errno == EAGAIN)
                continue;

            result = SIREH_EXEC_ERROR;
            break;
        }

        if (count == 0) {
            /*
             * EOF does not prove that the child has exited.
             * Check without blocking, then enforce the deadline.
             */
            int child_status = 0;
            pid_t waited = waitpid(child, &child_status, WNOHANG);

            if (waited == child) {
                close(pipefd[0]);

                if (!WIFEXITED(child_status)) {
                    free(buffer);
                    return SIREH_EXEC_ERROR;
                }

                output->data = buffer;
                output->length = used;
                output->child_exit_code = WEXITSTATUS(child_status);
                return SIREH_EXEC_OK;
            }

            if (waited < 0 && errno != EINTR) {
                result = SIREH_EXEC_ERROR;
                break;
            }

            /*
             * Child remains alive. Stop polling the closed pipe,
             * and wait only in short bounded intervals.
             */
            close(pipefd[0]);

            for (;;) {
                int64_t current = monotonic_ms();

                if (current < 0) {
                    result = SIREH_EXEC_ERROR;
                    break;
                }

                if (current - start >= (int64_t)timeout_ms) {
                    result = SIREH_EXEC_TIMEOUT;
                    break;
                }

                waited = waitpid(child, &child_status, WNOHANG);

                if (waited == child) {
                    if (!WIFEXITED(child_status)) {
                        free(buffer);
                        return SIREH_EXEC_ERROR;
                    }

                    output->data = buffer;
                    output->length = used;
                    output->child_exit_code = WEXITSTATUS(child_status);
                    return SIREH_EXEC_OK;
                }

                if (waited < 0 && errno != EINTR) {
                    result = SIREH_EXEC_ERROR;
                    break;
                }

                struct timespec pause = {
                    .tv_sec = 0,
                    .tv_nsec = 10000000L
                };

                (void)nanosleep(&pause, NULL);
            }

            /*
             * The descriptor was already closed above.
             * Avoid closing it twice during common cleanup.
             */
            pipefd[0] = -1;
            break;
        }

        if ((size_t)count > max_output - used) {
            result = SIREH_EXEC_OUTPUT_LIMIT;
            break;
        }

        memcpy(buffer + used, chunk, (size_t)count);
        used += (size_t)count;
    }

    if (result != SIREH_EXEC_OK)
        terminate_group(child);

    if (pipefd[0] >= 0)
        close(pipefd[0]);

    int status = 0;

    if (reap_child(child, &status) != 0) {
        free(buffer);
        return SIREH_EXEC_ERROR;
    }

    if (result != SIREH_EXEC_OK) {
        free(buffer);
        return result;
    }

    if (!WIFEXITED(status)) {
        free(buffer);
        return SIREH_EXEC_ERROR;
    }

    output->data = buffer;
    output->length = used;
    output->child_exit_code = WEXITSTATUS(status);

    return SIREH_EXEC_OK;
}


int sireh_exec_bounded(
    const char *const argv[],
    size_t max_output,
    unsigned int timeout_ms,
    struct sireh_exec_output *output
)
{
    return sireh_exec_internal(
        argv, -1, max_output, timeout_ms, output
    );
}

int sireh_exec_bounded_with_fd(
    const char *const argv[],
    int approved_fd,
    size_t max_output,
    unsigned int timeout_ms,
    struct sireh_exec_output *output
)
{
    if (approved_fd < 0)
        return SIREH_EXEC_ERROR;

    if (fcntl(approved_fd, F_GETFD) < 0)
        return SIREH_EXEC_ERROR;

    return sireh_exec_internal(
        argv, approved_fd, max_output, timeout_ms, output
    );
}
