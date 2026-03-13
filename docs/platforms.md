# Platform Support

Supported targets:

- native macOS on Mac mini
- Linux on standard servers and ARM devices such as Raspberry Pi

Guidance:

- keep the CLI and API identical across platforms
- let installers and doctor checks adapt to the host
- prefer the native install path on each platform
- use the containerized path only when it is genuinely simpler
