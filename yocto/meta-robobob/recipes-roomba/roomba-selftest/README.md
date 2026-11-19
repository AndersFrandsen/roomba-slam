# roomba-selftest

Bring-up check for the Roomba Open Interface, without ROS. Use it to verify the wiring through the level shifter and the serial link. Installed in both images.

Lift the Roomba off the dock first.

```bash
roomba-selftest
```

| Option | Default | Description |
|--------|---------|-------------|
| `--tx-gpio` | `23` | GPIO wired to Roomba RXD |
| `--rx-gpio` | `24` | GPIO wired to Roomba TXD |
| `--brc-gpio` | `25` | GPIO wired to Roomba BRC |

GPIO23/24 are not hardware UART pins, so the link is a software UART through `pigpiod`, which starts at boot.

## Checks

1. Link - finds the Roomba at 19200 baud, or switches it down from 115200. If neither answers, pulses BRC and tries once more
2. Battery - voltage, current, temperature, charge and charging state
3. Dock - fails if a charging source is present, as Safe mode exits while charging
4. Safe mode - enters Safe mode and confirms it
5. Song - plays three notes
6. LEDs and buttons - blinks the blue LED and fades the Power LED until CLEAN, SPOT or DOCK is pressed (20 s)

The Roomba is left in Passive mode with the LEDs off, so it charges and sleeps normally.

## Example output

```
root@robobob-zero2w:~# roomba-selftest
port    tx=GPIO23 rx=GPIO24 brc=GPIO25
link    19200 8N1 mode byte offset +1
battery 15.92 V -127 mA 21 C 1882/2068 mAh (91%) not charging
mode    safe
song    played
button  press CLEAN, SPOT or DOCK (keep the Roomba on the floor)
button  CLEAN
PASS
```

The `mode byte offset +1` line is normal for this Roomba: its firmware reports the OI mode one higher than the spec.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Pass |
| 10 | pigpiod not running or pigpio error |
| 20 | No response at 19200 or 115200, asleep? |
| 21 | Could not enter or left Safe mode |
| 22 | Short sensor reply |
| 30 | On the dock |
| 40 | No button press |

Don't run it while `robot.launch.py` is running; two programs on the same GPIOs corrupt each other's bytes.

## References

- [Create 2 / Roomba 600 Open Interface spec (PDF)](https://cdn.hackaday.io/files/1835247851890816/2021-04-13_iRobot_Roomba_600_Open_Interface_Spec-3.pdf)
- [pigpio bit-bang serial](https://abyz.me.uk/rpi/pigpio/)
