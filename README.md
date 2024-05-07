# Offline Orvibo/Gynoid ZigBee mini hub hack for Home Assistant

This repo contains some scripts to bypass the controller software
included with these hubs and replace them with a simple TCP relay.
The gateway software and much of the initial investigation into
this hub was possible thanks to [banksy-git/lidl-gateway-freedom](
https://github.com/banksy-git/lidl-gateway-freedom) and the blog
posts [Hacking the Silvercrest (Lidl) Smart Home Gateway](
https://paulbanks.org/projects/lidl-zigbee/) and
[Cloud-free integration with Home Assistant](
https://paulbanks.org/projects/lidl-zigbee/ha/).

## Hardware

This device is quite similar to the Tuya ones hardware-wise. Relevant chips are:

* SOC: Realtek RTL8196E
* ZigBee MCU: Silicon Labs EM3581
* Flash: Winbond 25Q128JVS

The PCB is marked "Mini HUB V2.1 2016-12-14" and has some test points for
UART TTL 3.3V for the SOC, and a JTAG header to the ZigBee MCU. I've only tested
UART to the SOC however. There's space on the board for a WiFi chip, but it's
been left unpopulated on this model.

The MCU and the SOC communicate via UART at 57600 bps with pins PB1 and PB2
on the MCU.

You can find pictures of the board and case in [res/images](./res/images/)

## Software

The software is pretty lousily built, constant writes to flash, most of the program
lives on a JFFS2 partition, I'm thinking that this won't last more than a year or two
by either running out of memory or wearing down the flash. The main ZigBee controller
software is referenced as "vihome" or "vihome2", I wasn't able to find any info
about it, it seems like it was custom built for this orvibo brand.

The root partition comes with standard busybox, ftpput, ftpget and nc, useful for
transferring files, no dropbear however, so I had to come up with some tricks to pipe
files via telnet.

To initialize the ZigBee MCU the vihome program writes the following values to
`/proc/gpio`:

```sh
echo jn_reset 1 > /proc/gpio
echo set_receiver_pid $$ > /proc/gpio
echo set_reset_ensure_time 5 > /proc/gpio
echo jn_reset 0 > /proc/gpio
```

`jn_reset` seems to be a reference to other board revisions that use a JN5168A
as the ZigBee MCU, setting it to zero enables the MCU and setting it to 1 disables
it. The baud rate to communicate with the MCU is 57600.

### Default credentials

* Username: `root`
* Password: `sidlee`

## Upgrading firmware on NCP

The device seems to have the ability to update the EmberZNet firmware from the same
UART port it uses for communication, however there seems to be some hardware error
where the RX line on the NCP is left floating when booting the bootloader.
The lack of a pull up resistor on this line means that the bus is effectively
unusable.

It's possible however to open the case and connect an external UART adapter with
a pull up resistor on its TX line and use that to communicate with the bootloader.
Baud rate for the bootloader is 115200 bps.

The three pads on top of the NCP as seen in [the top PCB view](res/images/pcb_top_1.png)
hook up to the same UART lines used by the SOC to communicate with the NCP.
From left to right the pads are: `GND`, `RX on the NCP` and `TX on the NCP`.
Keep in mind that regular communications (outside the bootloader), require
hardware flow control with the RTS and CTS lines. To avoid messing with the
RTS and CTS lines you can fire the bootloader from the serialgateway using
the bellows command like so: `bellows -d socket://<ip of the hub>:8888 bootloader`.

Once you connect via UART, press enter and you'll get the following prompt:

```
EFR 32Serial Btl v5.7.4.0 b99
1. upload ebl
2. run
3. ebl info
> 
```

The [walthowd/husbzb-firmware](https://github.com/walthowd/husbzb-firmware/tree/master)
repo [provides a script](
https://github.com/walthowd/husbzb-firmware/blob/d6a512ccb2d770d4fdabdc27805ddd68fde96988/ncp.py#L339)
to upload the firmware using XMODEM

[Here's](
https://github.com/grobasoz/zigbee-firmware/blob/a43872cf19a078712add54b34ecb44cd31ee6b46/EM3581/NCP_USW_EM3581-LR_678-57k6.ebl)
the latest firmware I was able to find for this chip, if you find something newer,
you're welcome to open an issue.

### Notes

Interestingly, with the current situation of the pull up resistors, it would seem
as though the SOC would be unable to update the NCP firmware on its own. I tried
running the function [update_zigbee](
res/dump/flash/from_mtd/mtdblock2-extracted/ProgramFiles/usr/local/bin/upgrade_functions.sh#L89-L116)
but I couldn't get it to work, the [JennicModuleProgrammer](
res/dump/flash/from_mtd/mtdblock2-extracted/ProgramFiles/usr/local/bin/JennicModuleProgrammer)
program messes with the GPIOs (`echo jn_update 1 > /proc/gpio`) to apparently set
the NCP into programming mode, but again the lack of a pull up resistor messes
with the UART bus anyways.

## TODO

* The whole jinja2 for scripts is kinda tedious since we're just using it to
  assign variables from the scripts, it'd be a better idea just render a variables
  and then source them from scripts.
* Allow for the install script to run after uninstalling, or have some sort of
  upgrade mechanism.
* Complete readme :P
* Add command to stop init process and install the mod from scratch.
* Allow for serialgateway to listen on localhost, that way SSH can be used
  to secure communications between HA and the ZigBee MCU

## Resources

* [YouTube: Smart Home Security Device: Mini Hub](
  https://www.youtube.com/watch?v=MCF9CpP_XHo): a look at the hardware
  for a different revision of this hub
* [4pda.to: Smart home - General topic](
  https://4pda.to/forum/index.php?showtopic=789600&st=3760#entry104809531):
  post showing the chips in a "Hommyn Zigbee Hub (HU-20-Z)", a rebrand of the
  orvibo hub. HW revision is V1.2
