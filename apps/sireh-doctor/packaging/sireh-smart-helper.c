/*
 * Sireh Doctor - Native SMART Helper
 *
 * DEVELOPMENT PROTOTYPE ONLY.
 * Opens a device read-only for validation; no SMART commands or privilege elevation.
 */

#define _XOPEN_SOURCE 700

#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <unistd.h>
#include "sireh-bounded-exec.h"

static int valid_device_argument(const char *path)
{
    const char *prefix = "/dev/";
    const size_t prefix_len = 5;

    if (path == NULL)
        return 0;

    if (strncmp(path, prefix, prefix_len) != 0)
        return 0;

    const char *name = path + prefix_len;

    if (*name == '\0')
        return 0;

    for (const unsigned char *p =
             (const unsigned char *)name; *p; ++p) {
        if (!isalnum(*p) && *p != '_' &&
            *p != '-' && *p != '.')
            return 0;
    }

    if (strcmp(name, ".") == 0 ||
        strcmp(name, "..") == 0)
        return 0;

    return 1;
}



static int valid_device_family(const char *path)
{
    const char *name = path + 5;
    const unsigned char *p = (const unsigned char *)name;

    if (strncmp(name, "sd", 2) == 0) {
        p += 2;

        if (*p < 'a' || *p > 'z')
            return 0;

        while (*p >= 'a' && *p <= 'z')
            ++p;

        return *p == '\0';
    }

    if (strncmp(name, "nvme", 4) == 0) {
        p += 4;

        if (!isdigit(*p))
            return 0;

        while (isdigit(*p))
            ++p;

        if (*p++ != 'n' || !isdigit(*p))
            return 0;

        while (isdigit(*p))
            ++p;

        return *p == '\0';
    }

    return 0;
}

static int valid_opened_disk(int fd, const char *device_path)
{
    struct stat opened;
    struct stat partition_node;
    char sysfs_path[PATH_MAX];
    char resolved[PATH_MAX];
    char virtual_root[PATH_MAX];
    char partition_path[PATH_MAX];
    char dev_path[PATH_MAX];
    char dev_numbers[64];
    unsigned int major_number;
    unsigned int minor_number;
    char trailing;
    FILE *stream;

    if (fstat(fd, &opened) != 0 || !S_ISBLK(opened.st_mode))
        return 0;

    if (snprintf(sysfs_path, sizeof(sysfs_path),
                 "/sys/dev/block/%u:%u",
                 major(opened.st_rdev),
                 minor(opened.st_rdev)) >= (int)sizeof(sysfs_path))
        return 0;

    if (realpath(sysfs_path, resolved) == NULL ||
        realpath("/sys/devices/virtual/block", virtual_root) == NULL)
        return 0;


    /*
     * Require the kernel's device subsystem to match the
     * expected disk family. This supplements descriptor and
     * sysfs identity checks; it is not sufficient on its own.
     */
    char subsystem_path[PATH_MAX];
    char subsystem_resolved[PATH_MAX];

    if (snprintf(subsystem_path, sizeof(subsystem_path),
                 "%s/device/subsystem", resolved) >=
        (int)sizeof(subsystem_path))
        return 0;

    if (realpath(subsystem_path, subsystem_resolved) == NULL)
        return 0;

    const char *subsystem = strrchr(subsystem_resolved, '/');

    if (subsystem == NULL)
        return 0;

    ++subsystem;

    if (strncmp(device_path, "/dev/sd", 7) == 0) {
        if (strcmp(subsystem, "scsi") != 0)
            return 0;
    } else if (strncmp(device_path, "/dev/nvme", 9) == 0) {
        if (strcmp(subsystem, "nvme") != 0)
            return 0;
    } else {
        return 0;
    }

    size_t root_len = strlen(virtual_root);

    if (strncmp(resolved, virtual_root, root_len) == 0 &&
        (resolved[root_len] == '/' || resolved[root_len] == '\0'))
        return 0;

    if (snprintf(partition_path, sizeof(partition_path),
                 "%s/partition", resolved) >= (int)sizeof(partition_path))
        return 0;

    if (lstat(partition_path, &partition_node) == 0)
        return 0;

    if (errno != ENOENT)
        return 0;

    if (snprintf(dev_path, sizeof(dev_path),
                 "%s/dev", resolved) >= (int)sizeof(dev_path))
        return 0;

    stream = fopen(dev_path, "r");

    if (stream == NULL)
        return 0;

    int scanned = fscanf(stream, "%63s", dev_numbers);
    fclose(stream);

    if (scanned != 1)
        return 0;

    if (sscanf(dev_numbers, "%u:%u%c",
               &major_number, &minor_number, &trailing) != 2)
        return 0;

    return major_number == major(opened.st_rdev) &&
           minor_number == minor(opened.st_rdev);
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "Exactly one device argument required\n");
        return 64;
    }

    if (!valid_device_argument(argv[1]) ||
        !valid_device_family(argv[1])) {
        fprintf(stderr, "Invalid or unsupported device path\n");
        return 64;
    }

    int fd = open(argv[1],
                  O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);

    if (fd < 0) {
        fprintf(stderr, "Cannot open device: %s\n", strerror(errno));
        return 77;
    }

    int valid = valid_opened_disk(fd, argv[1]);

    if (!valid) {
        close(fd);
        fprintf(stderr, "Not a supported physical whole-disk device\n");
        return 64;
    }

    /*
     * Defense in depth: confirm the device pathname still
     * identifies the block device held by the validated fd.
     * This does not replace descriptor-based SMART access.
     */
    struct stat opened_identity;
    struct stat pathname_identity;

    if (fstat(fd, &opened_identity) != 0 ||
        lstat(argv[1], &pathname_identity) != 0 ||
        !S_ISBLK(pathname_identity.st_mode) ||
        opened_identity.st_rdev != pathname_identity.st_rdev) {
        close(fd);
        fprintf(stderr, "Device identity changed during validation\\n");
        return 64;
    }

    /*
     * Fixed SMART information query using the validated
     * descriptor. No shell or user-defined options.
     */
    const char *const smart_args[] = {
        "/usr/sbin/smartctl",
        "--json=c",
        "-a",
        "/proc/self/fd/9",
        NULL
    };

    struct sireh_exec_output output = {0};

    int result = sireh_exec_bounded_with_fd(
        smart_args,
        fd,
        2U * 1024U * 1024U,
        20000U,
        &output
    );

    close(fd);

    if (result != SIREH_EXEC_OK) {
        free(output.data);
        fprintf(stderr, "SMART execution failed: %d\n", result);
        return result;
    }

    if (output.length == 0 || output.data == NULL) {
        free(output.data);
        fprintf(stderr, "SMART returned no JSON output\n");
        return 70;
    }

    size_t first = 0;

    while (first < output.length &&
           (output.data[first] == ' ' ||
            output.data[first] == '\n' ||
            output.data[first] == '\r' ||
            output.data[first] == '\t'))
        ++first;

    if (first == output.length || output.data[first] != '{') {
        free(output.data);
        fprintf(stderr, "SMART output is not JSON-like\n");
        return 70;
    }

    if (fwrite(output.data, 1, output.length, stdout)
        != output.length) {
        free(output.data);
        return 74;
    }

    free(output.data);
    return 0;
}
