"""Shared demo samples independent of the open log."""
from .telemetry import LAPS, RATE


def demo_samples():
    lap = LAPS[1]
    stop = 20 * RATE + 1
    return {key: lap[key][:stop].tolist() for key in ("t", "speed", "brake")}


def bokeh_speed(dark):
    # Only this worksheet needs the Bokeh engine.
    from bokeh.embed import json_item
    from bokeh.models import HoverTool
    from bokeh.plotting import figure

    data = demo_samples()
    p = figure(height=310, sizing_mode="stretch_width", toolbar_location=None,
               tools=[], x_range=(0, 20), y_range=(80, 220),
               x_axis_label="Time (s)", y_axis_label="Speed (km/h)")
    ink, grid, paper, blue = (("#afbdce", "#35424e", "#202833", "#8bb6ff") if dark
                              else ("#526276", "#e4e9ef", "#ffffff", "#245acd"))
    p.background_fill_color = p.border_fill_color = paper
    p.outline_line_color = None
    p.grid.grid_line_color = grid
    p.axis.axis_label_text_color = p.axis.major_label_text_color = ink
    p.axis.axis_line_color = p.axis.major_tick_line_color = grid
    p.axis.axis_label_text_font_style = "normal"
    trace = p.line(data["t"], data["speed"], line_color=blue, line_width=2)
    p.add_tools(HoverTool(renderers=[trace], mode="vline", line_policy="nearest",
                          tooltips=[("Time", "@x{0.00} s"), ("Speed", "@y{0.0} km/h")]))
    return json_item(p, "graph")
