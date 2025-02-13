from typing import Final, Iterable, Literal

from PIL import Image, ImageFont

from ... import _utils
from ...generator import FONT_BASE_PATH, Eta, ImageRenderer, Locale

FONT_NOTOSANS = ImageFont.FreeTypeFont(
    str(FONT_BASE_PATH.joinpath("NotoSansTC-Variable.ttf")))

FONT_ERR_L = _utils.get_variant(FONT_NOTOSANS, 26, "Bold")
FONT_NAME = _utils.get_variant(FONT_NOTOSANS, 28, "Bold")
FONT_STOP = _utils.get_variant(FONT_NOTOSANS, 16, "Bold")


class Epd3in8RenderBase(ImageRenderer):

    HEIGHT: Final = 480
    WIDTH: Final = 280
    BLACK: Final = 0x00
    WHITE: Final = 0xFF

    @staticmethod
    def text_min(locale: Locale, type_: Literal["s", "l"] = "s") -> str:
        if locale == Locale.EN:
            return "M" if type_ == "s" else "Minute"
        return "分" if type_ == "s" else "分鐘"

    @staticmethod
    def text_arr(locale: Locale) -> str:
        return "Arrving/Departing" if locale == Locale.EN else "即將抵達／已離開"

    def draw_error(self, message: str, degree: float = 0):
        canvas = Image.new('1', (self.WIDTH, self.HEIGHT), 255)
        draw = _utils.EtaImageDraw(canvas)
        draw.text_responsive(
            draw, message, (0, 0), (280, 480), FONT_ERR_L, position="c")

        return {"0-0-0": canvas.rotate(degree)}

    def six_row(self, etas: Iterable[Eta]):
        row_h = 80

        canvas = Image.new('1', (self.WIDTH, self.HEIGHT), 255)
        draw = _utils.EtaImageDraw(canvas)

        for row in range(1, 6):
            draw.line(((0, row * row_h), (self.WIDTH, row * row_h)))

        for row, route in enumerate(etas):
            draw.bitmap((3, row*row_h + 2.5),
                        Image.open(route.logo).convert("1").resize((30, 30)))
            draw.rectangle_wh((0, row*row_h), (35, 35))

            draw.text_responsive(route.no, (38, row*row_h),
                                 (112, 35), FONT_NAME)
            draw.text_responsive(
                route.destination, (0, 35 + row*row_h), (150, 22.5), FONT_STOP)
            draw.text_responsive(
                f"@{route.stop_name}", (0, 57.5 + row*row_h), (150, 22.5), FONT_STOP)

        return (canvas, draw, row_h)
