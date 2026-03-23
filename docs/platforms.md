# Platform Support

Supported targets:

- Linux Docker hosts for direct-to-MX delivery
- macOS and other developer machines for control-plane development and local testing

Guidance:

- keep the CLI and API identical across platforms
- use Docker Compose as the default runtime path
- prefer Linux for public internet delivery so the mail runtime has predictable access to ports and networking
- treat local desktop Docker environments as development conveniences, not the reference deployment
