# Sending Remote Keys

This project ships with a CLI (`samsungtv`) that can send remote keys and run common shortcuts against a Samsung TV over the network.

---

## Global Usage

```bash
samsungtv [OPTIONS] COMMAND [ARGS]...
```

### Required

- `--host TEXT` TV IP/host (**required**)

### Common Options

- `--port INTEGER` WebSocket port (`8001` / `8002`) (default: `8002`)
- `--token TEXT` Auth token
- `--token-file TEXT` Path to token file
- `--timeout FLOAT` Socket timeout seconds (`0` disables timeout) (default: `10`)
- `--key-press-delay FLOAT` Delay between key presses (seconds) (default: `1.0`)
- `--name TEXT` Client name shown on TV (default: `SamsungTvRemoteCli`)
- `--print-token / --no-print-token` Print token once if it is not saved (default: `print-token`)
- `-v, --verbose INTEGER` Increase verbosity (`-v`: INFO, `-vv`: DEBUG)

---

## Sending Raw Keys

### `send-key`

Send a raw `KEY_*` value.

**Signature**

```bash
samsungtv --host <TV_IP> send-key KEY_*
```

**Options**

- `--times INTEGER` Repeat count (min: `1`, default: `1`)
- `--cmd TEXT` `Click|Press|Release` (default: `Click`)
- `--delay FLOAT` Override key press delay (seconds, min: `0.0`)

**Examples**

```bash
# Click volume up once
samsungtv --host 192.168.1.50 send-key KEY_VOLUP

# Click volume up 5 times
samsungtv --host 192.168.1.50 send-key KEY_VOLUP --times 5

# Press (no release) + custom delay between repeats
samsungtv --host 192.168.1.50 send-key KEY_RIGHT --times 3 --cmd Press --delay 0.2

# Release a key
samsungtv --host 192.168.1.50 send-key KEY_RIGHT --cmd Release
```

> Notes
>
> - `--cmd` is normalized internally and only accepts: `Click`, `Press`, `Release`.
> - `--delay` overrides `--key-press-delay` for this invocation.

---

## Holding a Key

### `hold-key`

Hold a key for `N` seconds using: **Press -> sleep -> Release**.

**Signature**

```bash
samsungtv --host <TV_IP> hold-key KEY_* <seconds>
```

**Examples**

```bash
# Hold volume up for 5 seconds
samsungtv --host 192.168.1.50 hold-key KEY_VOLUP 5

# Hold left for 0.8 seconds
samsungtv --host 192.168.1.50 hold-key KEY_LEFT 0.8
```

---

## Shortcut Commands (Convenience Wrappers)

These map to `SamsungTVShortcuts` and send the corresponding keys for you.

### Power / Navigation / System

```bash
samsungtv --host 192.168.1.50 power     # KEY_POWER
samsungtv --host 192.168.1.50 home      # KEY_HOME
samsungtv --host 192.168.1.50 menu      # KEY_MENU
samsungtv --host 192.168.1.50 source    # KEY_SOURCE
samsungtv --host 192.168.1.50 back      # KEY_RETURN

samsungtv --host 192.168.1.50 up        # KEY_UP
samsungtv --host 192.168.1.50 down      # KEY_DOWN
samsungtv --host 192.168.1.50 left      # KEY_LEFT
samsungtv --host 192.168.1.50 right     # KEY_RIGHT
samsungtv --host 192.168.1.50 enter     # KEY_ENTER
```

### Audio

```bash
samsungtv --host 192.168.1.50 volume-up     # KEY_VOLUP
samsungtv --host 192.168.1.50 volume-down   # KEY_VOLDOWN
samsungtv --host 192.168.1.50 mute          # KEY_MUTE
```

### Channels

```bash
samsungtv --host 192.168.1.50 channel-up      # KEY_CHUP
samsungtv --host 192.168.1.50 channel-down    # KEY_CHDOWN
samsungtv --host 192.168.1.50 channel 7       # KEY_0–KEY_9 + KEY_ENTER
```

---

## Cursor (Mouse Device)

Some TVs expose a mouse-like device.

```bash
# Move cursor to X/Y
samsungtv --host 192.168.1.50 move-cursor 200 120

# Click (maps to KEY_ENTER)
samsungtv --host 192.168.1.50 mouse-click
```

---

## Factory / Service Menu (Dangerous)

### `factory`

Sends `KEY_FACTORY`. This can open service menus and may brick/misconfigure the TV.

```bash
# Requires explicit acknowledgement
samsungtv --host 192.168.1.50 factory --i-know-what-im-doing
```

If the acknowledgement flag is omitted, the CLI exits with an error.

---

## Typical Workflows

### Pairing / Token

Use `--token-file` to persist the token across runs:

```bash
samsungtv --host 192.168.1.50 --token-file .token device-info
```

### Faster Navigation Sequences

Reduce inter-key delay globally:

```bash
samsungtv --host 192.168.1.50 --key-press-delay 0.2 right
samsungtv --host 192.168.1.50 --key-press-delay 0.2 right
samsungtv --host 192.168.1.50 --key-press-delay 0.2 enter
```

Or override delay per raw key:

```bash
samsungtv --host 192.168.1.50 send-key KEY_RIGHT --times 5 --delay 0.15
```

---

## List of Commands

> **Note**
> This is not an official Samsung list. Some keys may not work depending on TV model or firmware.

---

### Power Key

```text
KEY_POWER
```

---

### Menus

```text
KEY_MENU
KEY_TOPMENU
KEY_TOOLS
KEY_HOME
KEY_HELP
KEY_CONTENTS
KEY_GUIDE
KEY_DISC_MENU
KEY_DVR_MENU
```

---

### Direction Keys

```text
KEY_UP
KEY_DOWN
KEY_LEFT
KEY_RIGHT
KEY_ENTER
KEY_RETURN
```

---

### Number Keys

```text
KEY_0
KEY_1
KEY_2
KEY_3
KEY_4
KEY_5
KEY_6
KEY_7
KEY_8
KEY_9
KEY_11
KEY_12
```

---

### Channel Keys

```text
KEY_CHUP
KEY_CHDOWN
KEY_PRECH
KEY_FAVCH
KEY_CH_LIST
KEY_AUTO_PROGRAM
KEY_MAGIC_CHANNEL
```

---

### Volume Keys

```text
KEY_VOLUP
KEY_VOLDOWN
KEY_MUTE
```

---

### Input Keys

```text
KEY_SOURCE
KEY_HDMI
KEY_COMPONENT1
KEY_COMPONENT2
KEY_AV1
KEY_AV2
KEY_AV3
KEY_SVIDEO1
KEY_SVIDEO2
KEY_SVIDEO3
KEY_FM_RADIO
KEY_DVI
KEY_DVR
KEY_TV
KEY_ANTENA
KEY_DTV
KEY_AMBIENT
```

---

### Media Keys

```text
KEY_REWIND
KEY_STOP
KEY_PLAY
KEY_FF
KEY_REC
KEY_PAUSE
KEY_LIVE
KEY_QUICK_REPLAY
KEY_STILL_PICTURE
KEY_INSTANT_REPLAY
```

---

### Extended Keys

```text
KEY_EXT1
KEY_EXT2
KEY_EXT3
KEY_EXT4
KEY_EXT5
KEY_EXT6
KEY_EXT7
KEY_EXT8
KEY_EXT9
KEY_EXT10
KEY_EXT11
...
KEY_EXT40
KEY_EXT41
```

---

### Other Keys

```text
KEY_GREEN
KEY_YELLOW
KEY_CYAN
KEY_ADDDEL
KEY_INFO
KEY_PIP_ONOFF
KEY_PIP_SWAP
KEY_PIP_SIZE
KEY_PIP_SCAN
KEY_PIP_CHUP
KEY_PIP_CHDOWN
KEY_PLUS100
KEY_CAPTION
KEY_PMODE
KEY_TTX_MIX
KEY_PICTURE_SIZE
KEY_AD
KEY_DEVICE_CONNECT
KEY_CONVERGENCE
KEY_FACTORY
KEY_3SPEED
KEY_RSURF
KEY_ASPECT
KEY_GAME
KEY_LINK
KEY_ANGLE
KEY_RESERVED1
KEY_ZOOM1
KEY_PROGRAM
KEY_BOOKMARK
KEY_PRINT
KEY_SUB_TITLE
KEY_CLEAR
KEY_VCHIP
KEY_REPEAT
KEY_DOOR
KEY_OPEN
KEY_WHEEL_LEFT
KEY_SLEEP
KEY_DMA
KEY_TURBO
KEY_MTS
KEY_PCMODE
KEY_TTX_SUBFACE
KEY_RED
KEY_DNIe
KEY_SRS
KEY_CONVERT_AUDIO_MAINSUB
KEY_MDC
KEY_SEFFECT
KEY_DTV_SIGNAL
KEY_PERPECT_FOCUS
KEY_ESAVING
KEY_WHEEL_RIGHT
KEY_VCR_MODE
KEY_CATV_MODE
KEY_DSS_MODE
KEY_TV_MODE
KEY_DVD_MODE
KEY_STB_MODE
KEY_CALLER_ID
KEY_SCALE
KEY_ZOOM_MOVE
KEY_CLOCK_DISPLAY
KEY_SETUP_CLOCK_TIMER
KEY_MAGIC_BRIGHT
KEY_W_LINK
KEY_DTV_LINK
KEY_APP_LIST
KEY_BACK_MHP
KEY_ALT_MHP
KEY_DNSe
KEY_RSS
KEY_ENTERTAINMENT
KEY_ID_INPUT
KEY_ID_SETUP
KEY_ANYNET
KEY_ANYVIEW
KEY_MS
KEY_MORE
KEY_PANNEL_POWER
KEY_PANNEL_CHUP
KEY_PANNEL_CHDOWN
KEY_PANNEL_VOLUP
KEY_PANNEL_VOLDOW
KEY_PANNEL_ENTER
KEY_PANNEL_MENU
KEY_PANNEL_SOURCE
KEY_ZOOM2
KEY_PANORAMA
KEY_4_3
KEY_16_9
KEY_DYNAMIC
KEY_STANDARD
KEY_MOVIE1
KEY_CUSTOM
KEY_AUTO_ARC_RESET
KEY_AUTO_ARC_LNA_ON
KEY_AUTO_ARC_LNA_OFF
KEY_AUTO_ARC_ANYNET_MODE_OK
KEY_AUTO_ARC_ANYNET_AUTO_START
KEY_AUTO_FORMAT
KEY_DNET
KEY_AUTO_ARC_CAPTION_ON
KEY_AUTO_ARC_CAPTION_OFF
KEY_AUTO_ARC_PIP_DOUBLE
KEY_AUTO_ARC_PIP_LARGE
KEY_AUTO_ARC_PIP_SMALL
KEY_AUTO_ARC_PIP_WIDE
KEY_AUTO_ARC_PIP_LEFT_TOP
KEY_AUTO_ARC_PIP_RIGHT_TOP
KEY_AUTO_ARC_PIP_LEFT_BOTTOM
KEY_AUTO_ARC_PIP_RIGHT_BOTTOM
KEY_AUTO_ARC_PIP_CH_CHANGE
KEY_AUTO_ARC_AUTOCOLOR_SUCCESS
KEY_AUTO_ARC_AUTOCOLOR_FAIL
KEY_AUTO_ARC_C_FORCE_AGING
KEY_AUTO_ARC_USBJACK_INSPECT
KEY_AUTO_ARC_JACK_IDENT
KEY_NINE_SEPERATE
KEY_ZOOM_IN
KEY_ZOOM_OUT
KEY_MIC
KEY_AUTO_ARC_CAPTION_KOR
KEY_AUTO_ARC_CAPTION_ENG
KEY_AUTO_ARC_PIP_SOURCE_CHANGE
KEY_AUTO_ARC_ANTENNA_AIR
KEY_AUTO_ARC_ANTENNA_CABLE
KEY_AUTO_ARC_ANTENNA_SATELLITE
```

---

## Documentation Source

This documentation was created based on the command reference published in:

https://tavicu.github.io/homebridge-samsung-tizen/extra/commands.html

The content was adapted and aligned to match the `samsungtvws` CLI behavior and command semantics.
