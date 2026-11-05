/*
 * Sireh Doctor - Native SMART Helper
 *
 * DEVELOPMENT PROTOTYPE ONLY.
 * No privileged execution, disk access, or SMART commands.
 */

#define _POSIX_C_SOURCE 200809L

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


static int valid_opened_disk(int fd)
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

    if (!valid_device_argument(argv[1])) {
        fprintf(stderr, "Invalid device path\n");
        return 64;
    }

    int fd = open(argv[1],
                  O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);

    if (fd < 0) {
        fprintf(stderr, "Cannot open device: %s\n", strerror(errno));
        return 77;
    }

    int valid = valid_opened_disk(fd);
    close(fd);

    if (!valid) {
        fprintf(stderr, "Not a supported physical whole-disk device\n");
        return 64;
    }

    puts("OPENED WHOLE-DISK VALIDATED - no SMART query executed");
    return 0;
}
