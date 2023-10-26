"""Control LEDs"""
import uasyncio as asyncio  # pyright: ignore [reportMissingImports]

from machine import Pin  # pyright: ignore [reportMissingImports]
from neopixel import NeoPixel as _NeoPixel  # pyright: ignore [reportMissingImports]

from .api import api
from .base import BaseDevice

DELAY = 500

DEFAULT_COLOR = (0, 0, 0)


class NeoPixel(BaseDevice):
    __doc__ = """A single color NeoPixel

    Args:
        name: A unique identifier for the LED strip
        pin: The pin to which the LED strip is connected.
        count: The number of LEDs in the strip. Default is 1
        blacklist: Indexes of LEDs to skip in the strip. Useful if you have a bad LED.
        default_brightness: The default brightness to set the NeoPixel(s)

    """

    def __init__(
        self,
        *,
        name: str,
        pin: int,
        count: int = 1,
        blacklist=None,
        default_brightness=None,
    ):
        self._length = count
        self._np = _NeoPixel(Pin(pin), count)
        self.blacklist = blacklist or []
        self._default_brightness = default_brightness or 0
        self._state = {
            v: (round(255 * self._default_brightness / 100),) * 3
            for v in range(len(self))
        }

        super().__init__(name, api)

        self.group.route("/set")(self.set)
        self.group.route("/on")(self.on)
        self.group.route("/off")(self.off)

        if self.__class__ == NeoPixel:
            asyncio.run(self.on())

    async def _write_to_neopixel(self, color_tuple):
        for idx in range(len(self)):
            if idx in self.blacklist:
                continue
            self._np[idx] = color_tuple
            self._state[idx] = color_tuple  # pyright: ignore [reportGeneralTypeIssues]
        self._np.write()
        await asyncio.sleep_ms(DELAY)

    @api.doc(
        """Set the brightness of the NeoPixel

        Args:
            brightness: How bright to set the Neopixel (0-100)

        """
    )
    async def set(self, *, brightness: int):
        brightness = int(brightness)
        await self._write_to_neopixel((round(255 * brightness / 100),) * 3)
        return {"brightness": brightness}

    @api.doc(
        """Turn on the NeoPixel, restoring its state""",
    )
    async def on(self):
        for idx in range(len(self)):
            if idx in self.blacklist:
                continue
            self._np[idx] = self._state[idx]
        self._np.write()
        await asyncio.sleep_ms(DELAY)
        return {}

    @api.doc(
        """Turn off the NeoPixel""",
    )
    async def off(self):
        for idx in range(len(self)):
            self._np[idx] = (0, 0, 0)
        self._np.write()
        return {}

    def __len__(self):
        return self._length


class RGBNeoPixel(NeoPixel):
    __doc__ = """An RGB NeoPixel

    Args:
        name: A unique identifier for the LED strip
        pin: The pin to which the LED strip is connected.
        count: The number of LEDs in the strip. Default is 1
        blacklist: Indexes of LEDs to skip in the strip. Useful if you have a bad LED.
        default_brightness: The default brightness to set the NeoPixel(s)
        default_color: The default color to apply to the RGB Neopixels
        default_on: Whether or not to turn the NeoPixel on by default

    """

    def __init__(
        self,
        *,
        name: str,
        pin: int,
        count: int = 1,
        blacklist=None,
        default_brightness=None,
        default_color=None,
        default_on=True,
    ):
        default_color = default_color or DEFAULT_COLOR
        if isinstance(default_color, str):
            default_color = COLOR_MAP[default_color]
        super().__init__(
            name=name,
            pin=pin,
            count=count,
            blacklist=blacklist,
            default_brightness=default_brightness,
        )
        self._default_color = tuple(
            round(v * self._default_brightness / 100) for v in default_color
        )
        self._state = {v: self._default_color for v in range(len(self))}
        if default_on:
            asyncio.run(self.on())

    @api.doc(
        """Set the color and brightness of the NeoPixel

        Args:
            red: The brightness value for the red channel (0-255)
            green: The brightness value for the green channel (0-255)
            blue: The brightness value for the blue channel (0-255)
            color: The name of a color
            brightness: A relative brightness scaling across all channels (0-100)

        """
    )
    async def set(
        self,
        *,
        red: int = None,
        green: int = None,
        blue: int = None,
        brightness: int = None,
        color: str = None,
    ):
        brightness = int(brightness or self._default_brightness or 100)
        if red or green or blue:
            if red is None or green is None or blue is None:
                raise ValueError(
                    "`red`, `green`, and `blue` must all be given if any are given."
                )
            color_tuple = (
                round(int(red) * brightness / 100),
                round(int(green) * brightness / 100),
                round(int(blue) * brightness / 100),
            )
        elif color:
            try:
                color_tuple = tuple(
                    round(v * brightness / 100)
                    for v in COLOR_MAP[color.lower().replace("grey", "gray")]
                )
            except KeyError:
                raise ValueError(f"Unknown color given: {color}")
        else:
            raise ValueError(
                "Either a `color` or values for `red`, `green`, and `blue` must be given"
            )

        await self._write_to_neopixel(color_tuple)
        return {
            "red": self._state[0][0],
            "green": self._state[0][1],
            "blue": self._state[0][2],
        }


class _OnboardLED(BaseDevice):
    """Control the Pico's onboard LED."""

    def __init__(self):
        self._led = Pin("LED", Pin.OUT)

    async def _loop(self, **_):
        while True:
            self._led.value(1)
            await asyncio.sleep(1)
            self._led.value(0)
            await asyncio.sleep(1)


COLOR_MAP = {
    "maroon": (128, 0, 0),
    "dark_red": (139, 0, 0),
    "brown": (165, 42, 42),
    "firebrick": (178, 34, 34),
    "crimson": (220, 20, 60),
    "red": (255, 0, 0),
    "tomato": (255, 99, 71),
    "coral": (255, 127, 80),
    "indian_red": (205, 92, 92),
    "light_coral": (240, 128, 128),
    "dark_salmon": (233, 150, 122),
    "salmon": (250, 128, 114),
    "light_salmon": (255, 160, 122),
    "orange_red": (255, 69, 0),
    "dark_orange": (255, 140, 0),
    "orange": (255, 165, 0),
    "gold": (255, 215, 0),
    "dark_golden_rod": (184, 134, 11),
    "golden_rod": (218, 165, 32),
    "pale_golden_rod": (238, 232, 170),
    "dark_khaki": (189, 183, 107),
    "khaki": (240, 230, 140),
    "olive": (128, 128, 0),
    "yellow": (255, 255, 0),
    "yellow_green": (154, 205, 50),
    "dark_olive_green": (85, 107, 47),
    "olive_drab": (107, 142, 35),
    "lawn_green": (124, 252, 0),
    "chartreuse": (127, 255, 0),
    "green_yellow": (173, 255, 47),
    "dark_green": (0, 100, 0),
    "green": (0, 128, 0),
    "forest_green": (34, 139, 34),
    "lime": (0, 255, 0),
    "lime_green": (50, 205, 50),
    "light_green": (144, 238, 144),
    "pale_green": (152, 251, 152),
    "dark_sea_green": (143, 188, 143),
    "medium_spring_green": (0, 250, 154),
    "spring_green": (0, 255, 127),
    "sea_green": (46, 139, 87),
    "medium_aqua_marine": (102, 205, 170),
    "medium_sea_green": (60, 179, 113),
    "light_sea_green": (32, 178, 170),
    "dark_slate_gray": (47, 79, 79),
    "teal": (0, 128, 128),
    "dark_cyan": (0, 139, 139),
    "aqua": (0, 255, 255),
    "cyan": (0, 255, 255),
    "light_cyan": (224, 255, 255),
    "dark_turquoise": (0, 206, 209),
    "turquoise": (64, 224, 208),
    "medium_turquoise": (72, 209, 204),
    "pale_turquoise": (175, 238, 238),
    "aqua_marine": (127, 255, 212),
    "powder_blue": (176, 224, 230),
    "cadet_blue": (95, 158, 160),
    "steel_blue": (70, 130, 180),
    "corn_flower_blue": (100, 149, 237),
    "deep_sky_blue": (0, 191, 255),
    "dodger_blue": (30, 144, 255),
    "light_blue": (173, 216, 230),
    "sky_blue": (135, 206, 235),
    "light_sky_blue": (135, 206, 250),
    "midnight_blue": (25, 25, 112),
    "navy": (0, 0, 128),
    "dark_blue": (0, 0, 139),
    "medium_blue": (0, 0, 205),
    "blue": (0, 0, 255),
    "royal_blue": (65, 105, 225),
    "blue_violet": (138, 43, 226),
    "indigo": (75, 0, 130),
    "dark_slate_blue": (72, 61, 139),
    "slate_blue": (106, 90, 205),
    "medium_slate_blue": (123, 104, 238),
    "medium_purple": (147, 112, 219),
    "dark_magenta": (139, 0, 139),
    "dark_violet": (148, 0, 211),
    "dark_orchid": (153, 50, 204),
    "medium_orchid": (186, 85, 211),
    "purple": (128, 0, 128),
    "thistle": (216, 191, 216),
    "plum": (221, 160, 221),
    "violet": (238, 130, 238),
    "magenta": (255, 0, 255),
    "fuchsia": (255, 0, 255),
    "orchid": (218, 112, 214),
    "medium_violet_red": (199, 21, 133),
    "pale_violet_red": (219, 112, 147),
    "deep_pink": (255, 20, 147),
    "hot_pink": (255, 105, 180),
    "light_pink": (255, 182, 193),
    "pink": (255, 192, 203),
    "antique_white": (250, 235, 215),
    "beige": (245, 245, 220),
    "bisque": (255, 228, 196),
    "blanched_almond": (255, 235, 205),
    "wheat": (245, 222, 179),
    "corn_silk": (255, 248, 220),
    "lemon_chiffon": (255, 250, 205),
    "light_golden_rod_yellow": (250, 250, 210),
    "light_yellow": (255, 255, 224),
    "saddle_brown": (139, 69, 19),
    "sienna": (160, 82, 45),
    "chocolate": (210, 105, 30),
    "peru": (205, 133, 63),
    "sandy_brown": (244, 164, 96),
    "burly_wood": (222, 184, 135),
    "tan": (210, 180, 140),
    "rosy_brown": (188, 143, 143),
    "moccasin": (255, 228, 181),
    "navajo_white": (255, 222, 173),
    "peach_puff": (255, 218, 185),
    "misty_rose": (255, 228, 225),
    "lavender_blush": (255, 240, 245),
    "linen": (250, 240, 230),
    "old_lace": (253, 245, 230),
    "papaya_whip": (255, 239, 213),
    "sea_shell": (255, 245, 238),
    "mint_cream": (245, 255, 250),
    "slate_gray": (112, 128, 144),
    "light_slate_gray": (119, 136, 153),
    "light_steel_blue": (176, 196, 222),
    "lavender": (230, 230, 250),
    "floral_white": (255, 250, 240),
    "alice_blue": (240, 248, 255),
    "ghost_white": (248, 248, 255),
    "honeydew": (240, 255, 240),
    "ivory": (255, 255, 240),
    "azure": (240, 255, 255),
    "snow": (255, 250, 250),
    "black": (0, 0, 0),
    "dim_gray": (105, 105, 105),
    "gray": (128, 128, 128),
    "dark_gray": (169, 169, 169),
    "silver": (192, 192, 192),
    "light_gray": (211, 211, 211),
    "gainsboro": (220, 220, 220),
    "white_smoke": (245, 245, 245),
    "white": (255, 255, 255),
}

# Add color temperature from: https://andi-siess.de/rgb-to-color-temperature/
COLOR_MAP.update(
    {
        "1000k": (255, 56, 0),
        "1100k": (255, 71, 0),
        "1200k": (255, 83, 0),
        "1300k": (255, 93, 0),
        "1400k": (255, 101, 0),
        "1500k": (255, 109, 0),
        "1600k": (255, 115, 0),
        "1700k": (255, 121, 0),
        "1800k": (255, 126, 0),
        "1900k": (255, 131, 0),
        "2000k": (255, 138, 18),
        "2100k": (255, 142, 33),
        "2200k": (255, 147, 44),
        "2300k": (255, 152, 54),
        "2400k": (255, 157, 63),
        "2500k": (255, 161, 72),
        "2600k": (255, 165, 79),
        "2700k": (255, 169, 87),
        "2800k": (255, 173, 94),
        "2900k": (255, 177, 101),
        "3000k": (255, 180, 107),
        "3100k": (255, 184, 114),
        "3200k": (255, 187, 120),
        "3300k": (255, 190, 126),
        "3400k": (255, 193, 132),
        "3500k": (255, 196, 137),
        "3600k": (255, 199, 143),
        "3700k": (255, 201, 148),
        "3800k": (255, 204, 153),
        "3900k": (255, 206, 159),
        "4000k": (255, 209, 163),
        "4100k": (255, 211, 168),
        "4200k": (255, 213, 173),
        "4300k": (255, 215, 177),
        "4400k": (255, 217, 182),
        "4500k": (255, 219, 186),
        "4600k": (255, 221, 190),
        "4700k": (255, 223, 194),
        "4800k": (255, 225, 198),
        "4900k": (255, 227, 202),
        "5000k": (255, 228, 206),
        "5100k": (255, 230, 210),
        "5200k": (255, 232, 213),
        "5300k": (255, 233, 217),
        "5400k": (255, 235, 220),
        "5500k": (255, 236, 224),
        "5600k": (255, 238, 227),
        "5700k": (255, 239, 230),
        "5800k": (255, 240, 233),
        "5900k": (255, 242, 236),
        "6000k": (255, 243, 239),
        "6100k": (255, 244, 242),
        "6200k": (255, 245, 245),
        "6300k": (255, 246, 247),
        "6400k": (255, 248, 251),
        "6500k": (255, 249, 253),
        "6600k": (254, 249, 255),
        "6700k": (252, 247, 255),
        "6800k": (249, 246, 255),
        "6900k": (247, 245, 255),
        "7000k": (245, 243, 255),
        "7100k": (243, 242, 255),
        "7200k": (240, 241, 255),
        "7300k": (239, 240, 255),
        "7400k": (237, 239, 255),
        "7500k": (235, 238, 255),
        "7600k": (233, 237, 255),
        "7700k": (231, 236, 255),
        "7800k": (230, 235, 255),
        "7900k": (228, 234, 255),
        "8000k": (227, 233, 255),
        "8100k": (225, 232, 255),
        "8200k": (224, 231, 255),
        "8300k": (222, 230, 255),
        "8400k": (221, 230, 255),
        "8500k": (220, 229, 255),
        "8600k": (218, 229, 255),
        "8700k": (217, 227, 255),
        "8800k": (216, 227, 255),
        "8900k": (215, 226, 255),
        "9000k": (214, 225, 255),
        "9100k": (212, 225, 255),
        "9200k": (211, 224, 255),
        "9300k": (210, 223, 255),
        "9400k": (209, 223, 255),
        "9500k": (208, 222, 255),
        "9600k": (207, 221, 255),
        "9700k": (207, 221, 255),
        "9800k": (206, 220, 255),
        "9900k": (205, 220, 255),
        "10000k": (207, 218, 255),
        "10100k": (207, 218, 255),
        "10200k": (206, 217, 255),
        "10300k": (205, 217, 255),
        "10400k": (204, 216, 255),
        "10500k": (204, 216, 255),
        "10600k": (203, 215, 255),
        "10700k": (202, 215, 255),
        "10800k": (202, 214, 255),
        "10900k": (201, 214, 255),
        "11000k": (200, 213, 255),
        "11100k": (200, 213, 255),
        "11200k": (199, 212, 255),
        "11300k": (198, 212, 255),
        "11400k": (198, 212, 255),
        "11500k": (197, 211, 255),
        "11600k": (197, 211, 255),
        "11700k": (197, 210, 255),
        "11800k": (196, 210, 255),
        "11900k": (195, 210, 255),
        "12000k": (195, 209, 255),
    }
)
