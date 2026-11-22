"""Desktop checks for the local viewer. Run with Python Playwright and Chrome."""
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright


def verify(browser, origin):
    page = browser.new_page(viewport={"width": 1280, "height": 820})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(origin + "/library?object=hist&frame=apple&content=fine")
    page.locator("#preview > dv-hist canvas").wait_for()
    objects = page.locator("#object option").evaluate_all("items => items.map(item => item.value)")
    assert {"scatter-density","scatter-size","frf","bits","susp-zones","rainbow-compare","telemetry-gps","sector-chart"} <= set(objects)
    for key in objects:
        page.select_option("#object", key)
        preview = page.locator("#preview > dv-" + key)
        preview.locator("canvas,table,.instrument").first.wait_for()
    for key in ("hist", "history", "scatter", "timing", "rainbow", "colour","scatter-size","bits","frf","hist-colour","rainbow-compare"):
        page.select_option("#object", key)
        component = page.locator("#preview > dv-" + key)
        canvas = component.locator("canvas")
        canvas.wait_for()
        canvas.focus()
        canvas.press("ArrowRight")
        page.wait_for_function("document.querySelector('#preview > *').selected !== null")
        if key=="scatter-size":
            assert "Brake (%)" in component.locator("output").inner_text()
        if key=="rainbow-compare":
            panes = component.evaluate("e => e.geometries.map(g=>g.box)")
            assert panes[0]["r"] < panes[1]["l"] and panes[0]["t"] == panes[1]["t"]
        expected_data = component.evaluate("e => e.data")
        expected_pick = component.evaluate("e => e.selected")
        def pixels():
            page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
            return canvas.evaluate("c => c.toDataURL()")
        renders = []
        for style in ("fine", "bold", "pattern"):
            page.select_option("#content", style)
            renders.append(pixels())
        assert len(set(renders)) == 3, key
        for frame in ("clean", "neumorphic", "apple"):
            page.select_option("#frame", frame)
            assert pixels() == renders[-1], (key, frame)
            assert component.evaluate("e => e.selected") == expected_pick
            assert component.evaluate("e => e.data") == expected_data

    page.select_option("#object", "hist")
    hist = page.locator("#preview > dv-hist")
    c = hist.locator("canvas")
    c.wait_for()
    c.focus()
    c.press("ArrowRight")
    assert hist.locator("output").inner_text()
    hist.get_by_role("button", name="Zoom in").click()
    first = hist.evaluate("e => e.range")
    c.press("Shift+ArrowRight")
    shifted = hist.evaluate("e => e.range")
    assert shifted[0] > first[0] and abs((shifted[1]-shifted[0])-(first[1]-first[0])) < 1e-8
    hist.get_by_role("button", name="Reset zoom").click()
    assert hist.evaluate("e => e.range") is None
    for key in ("hist","frf","rainbow-compare","bits","scatter-size"):
        page.select_option("#object", key)
        live = page.locator("#preview > dv-"+key)
        live.locator("canvas").wait_for()
        verify_export(browser,page,live,key)
    assert not errors, errors
    page.close()


def verify_export(browser,page,live,key):
    with tempfile.TemporaryDirectory() as temp:
        with page.expect_download() as download:
            page.click("#export")
        example = Path(temp) / (key+".html")
        download.value.save_as(example)
        offline = browser.new_page()
        offline.context.set_offline(True)
        offline.goto(example.as_uri())
        embedded = offline.locator("dv-"+key)
        embedded.locator("canvas").wait_for()
        assert embedded.evaluate("e => e.data") == live.evaluate("e => e.data")
        assert embedded.get_attribute("plot-style") == "pattern"
        embedded.locator("canvas").press("ArrowRight")
        assert embedded.locator("output").inner_text()
        offline.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        chrome = playwright.chromium.launch(channel="chrome")
        verify(chrome, sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8769")
        chrome.close()
        print("HTML components, frame/content independence, picking, zoom, pan and offline export passed.")
