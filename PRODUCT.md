# Data Viewer
<!-- impeccable:product-schema 1 -->

## Platform
web

## Purpose

Local interactive prototypes for choosing the design of a professional telemetry viewer. MoTeC i2 Pro worksheets and components are the functional reference. The interface, circuit, data and drawings are original. The final visual style is open.

## Prototype requirements

- Each worksheet is a portable HTML component. The library displays one at a time, with independent frame and plot styles. The plot style covers lines, markers, bars and grid. Units and selected values sit in the margins. Labels adapt to the available width.
- The embeddable library is one local JavaScript file. An HTML tag can declare its data, query, axes and appearance. The host may supply its own menus and consume selection and range events. Scatter can bind inline named columns offline or query a data service for a large recording. Changes to presentation reuse the displayed data.
- Compare Apple, Neumorphic and Clean in light and dark themes while preserving the worksheet, laps, axis and cursor position.
- Each demo address isolates one component, engine, gesture or style. Technical demos use a neutral appearance. Style demos use the same static plot and preserve workbook preferences. Demos always use synthetic samples, including when a real log is open.
- Explore a simulated session using active and reference laps, time- or distance-aligned traces, distributions, frequency plots, maps and reports. The prototype works with simulated data and imported files. Hardware acquisition and proprietary logs are outside its scope.
- Organise navigation by chart family around a central worksheet and linked sample inspector. Keep controls compact and keyboard accessible.
- Calculate figures in Python with NumPy and Plotly. Serve assets from disk through a loopback server. Display one composite figure at a time, render reports as HTML tables and show readings without requiring hover.
- Stream CSV conversion with Polars, publish caches atomically and read selected Parquet columns with PyArrow. Measure metadata opening, the first plot and subsequent navigation separately. Provide an interactive architecture diagram and a reproducible benchmark with workload-specific results.
- Verify sector times, lap deltas, sampling, FFT, distributions and catalogue coverage. Check the three styles on desktop in light and dark themes.
- One Windows launcher opens a dashboard with a shared route to the workbook, HTML library, demos and operating guide. The guide owns the interactive architecture map, plug-in instructions and index to the original studies and reference publications.
