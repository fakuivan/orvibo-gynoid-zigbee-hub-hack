# Offline Orvibo/Gynoid ZigBee mini hub hack for Home Assistant

This repo contains some scripts to bypass the controller software
included with these hubs and replace them with a simple TCP relay.
The gateway software and much of the initial investigation into
this hub was possible thanks to
[banksy-git/lidl-gateway-freedom](https://github.com/banksy-git/lidl-gateway-freedom)
and the blog posts
[Hacking the Silvercrest (Lidl) Smart Home Gateway](https://paulbanks.org/projects/lidl-zigbee/)
and
[Cloud-free integration with Home Assistant](https://paulbanks.org/projects/lidl-zigbee/ha/).

## Hardware

This device is quite similar to the Tuya ones hardware-wise. Relevant chips are:

* SOC: Realtek RTL8196E
* ZigBee MCU: Silicon Labs EM3581
* Flash: Winbond 25Q128JVS

The PCB is marked "Mini HUB V2.1 2016-12-14" and has some test points for
UART TTL 3.3V for the SOC, and a JTAG header to the ZigBee MCU. I've only tested
UART to the SOC however. There's space on the board for a WiFi chip, but it's
been left unpopulated on this model.

I haven't taken the time to fully determine how the MCU and the SOC communicate with
each other, it's not clear if it's TTL UART with flow control or if it's using SPI
and pumping serial communication and firmware updates trough that. My bet is that
it's using UART with flow control.

TODO: Board pictures

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

## TODO

* The whole jinja2 for scripts is kinda tedious since we're just using it to
  assign variables from the scripts, it'd be a better idea just render a variables
  and then source them from scripts.
* Allow for the install script to run after uninstalling, or have some sort of
  upgrade mechanism.
* Complete readme :P
* Add command to stop init process and install the mod from scratch.

## Resources

* [YouTube: Smart Home Security Device: Mini Hub](https://www.youtube.com/watch?v=MCF9CpP_XHo): a look at the hardware for a different revision of this hub
* [4pda.to: Smart home - General topic](https://4pda.to/forum/index.php?showtopic=789600&st=3760#entry104809531): post showing the chips in a "Hommyn Zigbee Hub (HU-20-Z)", a rebrand of the orvibo hub. HW revision is V1.2