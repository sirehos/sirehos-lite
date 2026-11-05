# Sireh Doctor — Native SMART Helper Security Specification

Status: DEVELOPMENT DESIGN — NOT APPROVED FOR PRIVILEGED DEPLOYMENT

## Purpose

Allow Sireh Doctor to collect disk SMART information while keeping
the graphical application unprivileged.

## Installation requirements

- Install the native executable at:
  `/usr/libexec/sireh-doctor/sireh-smart-helper`
- Executable and parent directories must be root-owned.
- Ordinary users must not be able to modify the executable or
  any component of its installation path.
- Do not use a setuid bit on the Sireh helper.
- Never elevate an executable from a user-writable development tree.
- Installation must use trusted packaging and verified permissions.

## Authorization

- Use a dedicated PolicyKit action for SMART collection.
- Require explicit authorization under a reviewed policy.
- Do not authorize arbitrary executables, scripts or shell commands.
- Do not assume that GUI authentication alone validates disk arguments.
- Reject unsupported devices and malformed arguments.

## Device access

- Accept only explicitly supported whole-disk device classes.
- Validate the opened device using fstat and kernel device identity.
- Reject partitions, virtual devices and unsupported device types.
- Prevent pathname substitution between validation and SMART access.
- Do not assume all SATA, SAS, USB and NVMe transports behave alike.

## SMART execution

- Invoke only a trusted, fixed smartctl executable.
- Use a fixed, reviewed argument list.
- Do not invoke a shell.
- Apply a bounded execution timeout.
- Limit output size and handle malformed JSON safely.
- Do not initiate SMART self-tests, repairs or configuration changes.
- Treat SMART collection as observational, while recognizing that
  hardware commands can still have device-specific side effects.

## Privilege boundary

- Keep the Qt GUI and ordinary diagnostics unprivileged.
- Do not add users to the disk group.
- Avoid inheriting untrusted environment variables or file descriptors.
- Review process credentials, privilege retention and error handling.
- Audit all authorization and installation files before activation.

## Release gate

Privileged execution remains disabled until:

1. Device validation is tested on actual supported hardware.
2. Descriptor-safe SMART execution is demonstrated.
3. PolicyKit authorization is reviewed and tested.
4. Root-owned packaging and permissions are verified.
5. Negative security tests and application regression tests pass.
6. A security review approves the resulting implementation.
