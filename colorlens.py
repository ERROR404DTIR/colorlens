#!/usr/bin/env python3
"""colorlens - convert colors, check WCAG contrast and generate shades.

Usage:
  colorlens show ff8800
  colorlens show "#ff8800"
  colorlens show "rgb(255, 136, 0)"
  colorlens show "hsl(32, 100%, 50%)"
  colorlens contrast 1a1a1a ffffff
  colorlens shades 3b82f6 -n 9

Note: quote values that start with '#' or contain spaces/parentheses.
"""
import argparse
import colorsys
import re
import sys

NUM = r"(\d+(?:\.\d+)?)"


def parse(value):
    """Return an (r, g, b) tuple from a hex, rgb() or hsl() string."""
    s = value.strip().lower()
    m = re.fullmatch(r"#?([0-9a-f]{3}|[0-9a-f]{6})", s)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = re.fullmatch(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", s)
    if m:
        rgb = tuple(int(x) for x in m.groups())
        if max(rgb) > 255:
            raise ValueError(f"rgb values must be 0-255: {value!r}")
        return rgb
    m = re.fullmatch(rf"hsl\(\s*{NUM}\s*,\s*{NUM}%\s*,\s*{NUM}%\s*\)", s)
    if m:
        h, sat, lum = (float(x) for x in m.groups())
        if h > 360 or sat > 100 or lum > 100:
            raise ValueError(f"hsl out of range: {value!r}")
        r, g, b = colorsys.hls_to_rgb(h / 360, lum / 100, sat / 100)
        return tuple(round(x * 255) for x in (r, g, b))
    raise ValueError(f"cannot parse color: {value!r}")


def to_hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


def to_hsl(rgb):
    h, lum, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    return round(h * 360) % 360, round(s * 100), round(lum * 100)


def luminance(rgb):
    """Relative luminance as defined by WCAG 2.x."""
    def chan(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (chan(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def swatch(rgb):
    if not sys.stdout.isatty():
        return ""
    return "\x1b[48;2;%d;%d;%dm    \x1b[0m " % tuple(rgb)


def cmd_show(a):
    rgb = parse(a.color)
    h, s, lum = to_hsl(rgb)
    print(f"{swatch(rgb)}{to_hex(rgb)}")
    print(f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})")
    print(f"hsl({h}, {s}%, {lum}%)")
    for name, other in (("white", (255, 255, 255)), ("black", (0, 0, 0))):
        print(f"contrast on {name}: {contrast(rgb, other):.2f}:1")


def cmd_contrast(a):
    fg, bg = parse(a.foreground), parse(a.background)
    ratio = contrast(fg, bg)
    print(f"{swatch(fg)}{to_hex(fg)} on {swatch(bg)}{to_hex(bg)}")
    print(f"ratio: {ratio:.2f}:1")
    for label, need in (("AA normal text", 4.5), ("AA large text", 3.0),
                        ("AAA normal text", 7.0), ("AAA large text", 4.5)):
        print(f"  {label:<16} {'PASS' if ratio >= need else 'FAIL'} (needs {need}:1)")
    return 0 if ratio >= 4.5 else 1


def cmd_shades(a):
    if a.n < 2:
        raise ValueError("-n must be at least 2")
    rgb = parse(a.color)
    h, _, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    for i in range(a.n):
        lum = (95 - i * 90 / (a.n - 1)) / 100
        shade = tuple(round(x * 255) for x in colorsys.hls_to_rgb(h, lum, s))
        print(f"{swatch(shade)}{to_hex(shade)}  L={round(lum * 100)}%")


def main(argv=None):
    p = argparse.ArgumentParser(prog="colorlens", description="Color converter, WCAG contrast checker and shade generator.")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show", help="convert a color to hex / rgb / hsl")
    s.add_argument("color")
    s.set_defaults(func=cmd_show)
    c = sub.add_parser("contrast", help="WCAG contrast ratio (exit 1 if below AA)")
    c.add_argument("foreground")
    c.add_argument("background")
    c.set_defaults(func=cmd_contrast)
    d = sub.add_parser("shades", help="print lighter-to-darker shades of a color")
    d.add_argument("color")
    d.add_argument("-n", type=int, default=9, help="number of shades (default 9)")
    d.set_defaults(func=cmd_shades)
    a = p.parse_args(argv)
    try:
        return a.func(a) or 0
    except ValueError as e:
        print(f"colorlens: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
