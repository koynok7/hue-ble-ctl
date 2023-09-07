#!/usr/bin/env python
import sys

import dbus
import gatt
import struct
from typing import List
from threading import Thread, Barrier
import multiprocessing
from rgbxy import Converter, GamutC, get_light_gamut
from struct import pack, unpack

LIGHT_CHARACTERISTIC = "932c32bd-0002-47a2-835a-a8d455b859dd"
BRIGHTNESS_CHARACTERISTIC = "932c32bd-0003-47a2-835a-a8d455b859dd"
TEMPERATURE_CHARACTERISTIC = "932c32bd-0004-47a2-835a-a8d455b859dd"
MANUFACTURER_UUID = "00002a29-0000-1000-8000-00805f9b34fb"
MODEL_CHARACTERISTIC = "00002a24-0000-1000-8000-00805f9b34fb"
FIRMWARE_UUID = "00002a28-0000-1000-8000-00805f9b34fb"
BULB_STATE_UUID = "932c32bd-0007-47a2-835a-a8d455b859dd"
COLOR_CHARACTERISTIC = "932c32bd-0005-47a2-835a-a8d455b859dd"


#def convert_xyz_to_xy(r: int, g: int, b: int):

#    """
#    Returns xy values in the CIE 1931 colorspace after a RGB to XYZ conversion using Wide RGB D65 conversion formula been applied.
#    """
#    X = r * 0.649926 + g * 0.103455 + b * 0.197109
#    Y = r * 0.234327 + g * 0.743075 + b * 0.022598
#    Z = r * 0.0000000 + g * 0.053077 + b * 1.035763
#
#    x = round(X / (X + Y + Z), 4)
#    y = round(Y / (X + Y + Z), 4)
#    return x, y


class HueLight(gatt.Device):
    def __init__(
        self, action: str, extra_args: List[str], mac_address: str, manager: gatt.DeviceManager,
        barrier: Barrier
    ) -> None:
        self.action = action
        self.extra_args = extra_args
        self.barrier = barrier

        print(f"Connecting to {mac_address}...")
        super(HueLight, self).__init__(mac_address=mac_address, manager=manager)

    def introspect(self) -> None:
        for s in self.services:
            print(f"service: {s.uuid}")
            for c in s.characteristics:
                val = c.read_value()
                if val is not None:
                    ary = bytearray()
                    for i in range(len(val)):
                        ary.append(int(val[i]))
                    try:
                        val = ary.decode("utf-8")
                    except UnicodeDecodeError:
                        val = ary
                print(f"  characteristic: {c.uuid}: {val}")
    
    def state(self) -> None:
        for s in self.services:
            for c in s.characteristics:
                val = c.read_value()
                
                if val is not None:
                    ary = bytearray()
                    for i in range(len(val)):
                        ary.append(int(val[i]))
                    try:
                        val = ary.decode("utf-8")
                    except UnicodeDecodeError:
                        val = ary

                uuid_str = str(c.uuid)
                if uuid_str == MANUFACTURER_UUID:
                    print(f"Manufacturer: {val}")
                elif uuid_str == MODEL_CHARACTERISTIC:
                    print(f"Model: {val}")
                elif uuid_str == FIRMWARE_UUID:
                    print(f"Firmware Version: {val}")
                elif uuid_str == BULB_STATE_UUID:
                    # State of the Bulb
                    state = "ON" if ary[2] == 0x01 else "OFF"
                    
                    # Brightness
                    brightness = int(ary[5] / 255 * 100)
                    
                    # RGB Conversion from XY || Stil under development! Values not aacurate
                    #x, y = ary[-1], ary[-2]
                    #r, g, b = self.converter.xy_to_rgb(x, y)  
                    # Using the converter that is used in the set_color_rgb function
                    
                    # Displaying the parsed values
                    print(f"Bulb State: {state}")
                    print(f"Brightness: {brightness}%")
                    #print(f"RGB: {r} {g} {b}")
                    #The color XY coordinates should be in the 
                    #932c32bd-0005-47a2-835a-a8d455b859dd 
                    #characterisctic last two bytes, tests needed
    
    def set_color_rgb(self, r, g, b):
        #setting the color with this function is NOT always accurate
        x, y = self.converter.rgb_to_xy(r, g, b)
        self.set_color_xy(x, y)
        print(self.color.read_value())
        print("Color was set to " + self.extra_args[0] + " " + self.extra_args[1] + " " + self.extra_args[2])
        
    def set_color_xy(self, x, y) -> None:
        val = pack('<HH', int(x * 0xFFFF), int(y * 0xFFFF))
        self.color.write_value(val)

    def set_temperature(self, val: int) -> None:
        val = max(153, min(val, 454))
        self.temperature.write_value(struct.pack("h", val))
        print(self.temperature.read_value())

    def set_brightness(self, val: int) -> None:
        self.brightness.write_value(struct.pack("B", val))
        print(self.brightness.read_value())

    def toggle_light(self) -> None:
        val = self.light_state.read_value()
        if val is None:
            msg = (
                "Could not read characteristic. If that is your first pairing"
                "you may need to perform a firmware reset using the mobile phillips hue app and try connect again: "
                "https://www.reddit.com/r/Hue/comments/eq0y3y/philips_hue_bluetooth_developer_documentation/"
            )
            print(msg, file=sys.stderr)
            sys.exit(1)
        on = val[0] == 1
        self.light_state.write_value(b"\x00" if on else b"\x01")

    def light_on(self) -> None:
        val = self.light_state.read_value()
        if val is None:
            msg = (
                "Could not read characteristic. If that is your first pairing"
                "you may need to perform a firmware reset using the mobile phillips hue app and try connect again: "
                "https://www.reddit.com/r/Hue/comments/eq0y3y/philips_hue_bluetooth_developer_documentation/"
            )
            print(msg, file=sys.stderr)
            sys.exit(1)
        on = val[0] == 1
        self.light_state.write_value(b"\x01")

    def light_off(self) -> None:
        val = self.light_state.read_value()
        if val is None:
            msg = (
                "Could not read characteristic. If that is your first pairing"
                "you may need to perform a firmware reset using the mobile phillips hue app and try connect again: "
                "https://www.reddit.com/r/Hue/comments/eq0y3y/philips_hue_bluetooth_developer_documentation/"
            )
            print(msg, file=sys.stderr)
            sys.exit(1)
        on = val[0] == 1
        self.light_state.write_value(b"\x00")

    def services_resolved(self) -> None:
        super().services_resolved()
        for s in self.services:
            for char in s.characteristics:
                if char.uuid == LIGHT_CHARACTERISTIC:
                    self.light_state = char
                elif char.uuid == BRIGHTNESS_CHARACTERISTIC:
                    self.brightness = char
                elif char.uuid == TEMPERATURE_CHARACTERISTIC:
                    self.temperature = char
                elif char.uuid == COLOR_CHARACTERISTIC:
                    self.color = char
                elif char.uuid == MODEL_CHARACTERISTIC:
                    self.model = char
        try:
            self.converter = Converter(get_light_gamut(self.model))
        except ValueError:
            self.converter = Converter(GamutC)
        if self.action == "toggle":
            self.toggle_light()
        elif self.action == "switch_on":
            self.light_on()
        elif self.action == "switch_off":
            self.light_off()
        elif self.action == "introspect":
            self.introspect()
        elif self.action == "state":
            self.state()
        elif self.action == "temperature":
            self.set_temperature(int(self.extra_args[0]))
        elif self.action == "brightness":
            self.set_brightness(int(self.extra_args[0]))
        elif self.action == "col_xy":
            self.set_color_xy(float(self.extra_args[0]),float(self.extra_args[1]))
        elif self.action == "color":
            self.set_color_rgb(float(self.extra_args[0]),float(self.extra_args[1]),float(self.extra_args[2]))
        else:
            print(f"Unknown action: {self.action}")
            sys.exit(1)
        self.barrier.wait()

def main():
    if len(sys.argv) < 3:
        print(f"USAGE: {sys.argv[0]} toggle|switch_on|switch_off|brightness|temperature|introspect macaddress args...", file=sys.stderr)
        sys.exit(1)

    mac_address = sys.argv[2]
    # FIXME adapter_name should be configurable
    manager = gatt.DeviceManager(adapter_name="hci0")
    # this is a bit of a hack. gatt blocks indefinitely
    b = Barrier(2)
    device = HueLight(sys.argv[1], sys.argv[3:], mac_address=mac_address, manager=manager, barrier=b)
    def run():
        device.connect()
        manager.run()
    t = Thread(target=run, daemon=True)
    t.start()
    b.wait()




if __name__ == "__main__":
    mainProcess = multiprocessing.Process(target=main)
    mainProcess.start()
    #The process runs infinetly, if the device is not connected,
    #or there is an error. This part should take care of that.
    mainProcess.join(10)
    if mainProcess.is_alive():
        mainProcess.terminate()
        print ("Timeout reached or an error encountered. Exiting...")
        # Could use mainProcess.kill() but not advised
