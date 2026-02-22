<p align="center">
  <img src="https://raw.githubusercontent.com/xchwarze/samsung-tv-ws-api/master/assets/logo.png" width="300px" border="0" />
  <br/>
  Samsung Smart TV WS API wrapper
  <a href="https://github.com/xchwarze/samsung-tv-ws-api/releases/latest">
    <img src="https://img.shields.io/github/v/release/xchwarze/samsung-tv-ws-api?display_name=tag&sort=semver&style=flat-square" alt="Version">
  </a>
  <a href="https://github.com/xchwarze/samsung-tv-ws-api/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/xchwarze/samsung-tv-ws-api/ci.yml?branch=master&style=flat-square" alt="Lint & Tests">
  </a>
</p>

This project is a Python library for remotely controlling Samsung televisions via a TCP/IP connection.

It supports modern (post-2016) Samsung Smart TVs running **Tizen OS**, connected via Ethernet or Wi-Fi.

---

## Documentation

Most of the general usage and features are documented in this README.
Some advanced topics are covered in dedicated documents:

- **[Commands](./COMMANDS.md)**  
  Detailed remote key reference, including the full key list and all supported ways to send keys via the CLI.

- **[Applications (App IDs)](./APPLICATIONS.md)**  
  Extended documentation about application IDs, how to find them, and how to install or launch applications from the TV.

## Features

- WebSocket and REST APIs
- Sync and async support
- Encrypted v1 API support for older TVs
- Full Art Mode support (Frame TVs)
- Command-line interface (CLI)

---

## Installation

Requires **Python >= 3.9**.

### Install from PyPI (recommended)

Core library:

```bash
pip install samsungtvws
```

Common install (async + encrypted + CLI):

```bash
pip install "samsungtvws[async,encrypted,cli]"
```

---

### Optional extras

- `async`: async I/O support (`aiohttp`, `websockets`)
- `encrypted`: v1 encrypted API support for older Orsay TVs (`cryptography`, `py3rijndael`)
- `cli`: installs the `samsungtv` command (`typer`, `wakeonlan`)

Examples:

```bash
pip install "samsungtvws[cli]"
pip install "samsungtvws[async]"
pip install "samsungtvws[encrypted]"
```

---

### Install from GitHub (latest main branch)

```bash
pip install "git+https://github.com/xchwarze/samsung-tv-ws-api.git#egg=samsungtvws[async,encrypted,cli]"
```

---

### Local development install

```bash
git clone https://github.com/xchwarze/samsung-tv-ws-api.git
cd samsung-tv-ws-api
pip install --editable ".[async,encrypted,cli]"
```

`--editable` installs the package in development mode and can be omitted for a regular local install.

---

### CLI check

If installed with the `cli` extra:

```bash
samsungtv --help
```

---

## Usage

This library can be used either programmatically or via the CLI, depending on the integration needs.

### Programmatic usage

For custom integrations or advanced control flows, the library can be consumed directly from Python code.

The `examples/` directory contains **ready-to-run programmatic examples**, including:

- WebSocket and REST usage
- Async integrations
- Encrypted API usage
- Art Mode control

Reviewing these examples is the recommended starting point for manual integrations.

---

### CLI usage

For quick testing, automation, or scripting, the library provides a fully featured **command-line interface**.
Requires installation with the `cli` extra.

Once installed:

```bash
samsungtv --help
```

#### CLI examples

Power on TV using Wake-on-LAN:

```bash
samsungtv --host 192.168.1.50 wol
```

Toggle power:

```bash
samsungtv --host 192.168.1.50 power
```

List installed applications:

```bash
samsungtv --host 192.168.1.50 apps
```

Run an application by ID:

```bash
samsungtv --host 192.168.1.50 app-run 3201606009684
```

Open a URL in the TV browser:

```bash
samsungtv --host 192.168.1.50 open-browser https://duckduckgo.com
```

Get device information:

```bash
samsungtv --host 192.168.1.50 device-info
```

Enable Art Mode:

```bash
samsungtv --host 192.168.1.50 art-mode on
```

Upload an image to Art Mode:

```bash
samsungtv --host 192.168.1.50 art-upload image.jpg
```

The CLI exposes most of the library functionality, including:

- App management
- Remote control keys
- Device information
- Wake-on-LAN
- Full Art Mode management

## Supported TVs

This library is designed to support **all Samsung Smart TVs running Tizen OS** (2016+).

It also provides support for older **Orsay-based TVs**, specifically:

- **H series (2014)**
- **Part of J series (2015)**

Support for Orsay devices is mainly provided through the encrypted v1 API.

Official Samsung compatibility references:

- [https://developer.samsung.com/smarttv/develop/extension-libraries/smart-view-sdk/supported-device/supported-tvs.html](https://developer.samsung.com/smarttv/develop/extension-libraries/smart-view-sdk/supported-device/supported-tvs.html)
- [https://developer.samsung.com/smarttv/develop/specifications/tv-model-groups.html](https://developer.samsung.com/smarttv/develop/specifications/tv-model-groups.html)

## Known issues and restrictions

### Subnet / VLAN

Samsung Smart TVs do not allow WebSocket connections across different subnets or VLANs.
If your TV is not on the same subnet as Home Assistant, the connection may fail.

Depending on the network setup, this limitation might be mitigated using:

- IP masquerading (NAT)
- A proxy

### Samsung TV keeps asking for permission

The default setting on newer televisions is to ask for permission on every connection
attempt.

To avoid this behavior, adjust:

**Device Connection Manager → Access Notification Settings → First Time Only**

It is also recommended to clean up previous attempts in:

**Device Connection Manager → Device List**

## Patreon and Tips!

(I have this block in all my GPL projects)
Those who want to help buy testing hardware or just give me a tip, you can do it by sending donations to my Binance account.
I also made a [Patreon](https://www.patreon.com/xchwarze)

[![patreon](https://raw.githubusercontent.com/xchwarze/samsung-tv-ws-api/master/assets/patreon.png)](https://www.patreon.com/xchwarze)
![binance-qr](https://raw.githubusercontent.com/xchwarze/samsung-tv-ws-api/master/assets/binance-qr.png)

## License

LGPL-3.0
