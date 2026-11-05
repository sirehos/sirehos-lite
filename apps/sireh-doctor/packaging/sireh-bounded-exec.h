#ifndef SIREH_BOUNDED_EXEC_H
#define SIREH_BOUNDED_EXEC_H

#include <stddef.h>

/*
 * Native bounded execution interface.
 *
 * Intended for fixed, reviewed executable paths and arguments.
 * No shell interpretation, user-supplied command strings,
 * or elevated execution from the development directory.
 *
 * Implementation and security review are pending.
 */

enum sireh_exec_result {
    SIREH_EXEC_OK = 0,
    SIREH_EXEC_OUTPUT_LIMIT = 75,
    SIREH_EXEC_TIMEOUT = 124,
    SIREH_EXEC_ERROR = 70
};

struct sireh_exec_output {
    unsigned char *data;
    size_t length;
    int child_exit_code;
};

/*
 * Execute a fixed command with bounded output and runtime.
 *
 * On success, the caller owns output->data and must free it.
 * On failure, no partial output may be returned.
 *
 * This is a proposed API, not yet an implemented function.
 */
int sireh_exec_bounded(
    const char *const argv[],
    size_t max_output,
    unsigned int timeout_ms,
    struct sireh_exec_output *output
);

/*
 * Reserved descriptor number in the executed child.
 *
 * The implementation must duplicate the caller-approved
 * descriptor to this exact number, close all other
 * nonstandard descriptors, and clear FD_CLOEXEC only
 * for this child-side descriptor.
 *
 * The caller remains responsible for validating the
 * original descriptor before invoking this API.
 */
#define SIREH_EXEC_DEVICE_FD 9

/*
 * Execute with exactly one explicitly approved descriptor.
 *
 * approved_fd must already be open and validated by
 * the caller. A negative descriptor is invalid.
 *
 * This interface is declared but NOT YET IMPLEMENTED.
 * Do not call it until implementation and tests pass.
 */
int sireh_exec_bounded_with_fd(
    const char *const argv[],
    int approved_fd,
    size_t max_output,
    unsigned int timeout_ms,
    struct sireh_exec_output *output
);

#endif
