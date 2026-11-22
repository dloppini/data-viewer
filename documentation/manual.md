# Data Viewer

User manual and technical reference

Desktop edition · 22 November 2026

## Quick start

Start in `C:\Code\Data Viewer`. Double-click **Start Data Viewer.cmd**. It starts the local Python service and opens the dashboard in your browser. On a fresh Windows installation it uses Python 3.12 to create the project environment and installs the packages in `requirements.txt`. Initial setup needs pip access. The installed viewer runs locally.

| Workspace | What to do there |
| --- | --- |
| Dashboard | Read this guide, explore the system map, open the examples and download the manual. |
| Workbook | Inspect the simulated session or open your own CSV or Parquet recording. |
| HTML library | Try a single component, change its frame and plot style, and export an embeddable example. |
| Demos | Compare one chart, plotting engine, interaction or style at a time using synthetic telemetry. |

### Your first lap comparison

1. Open **Workbook** and choose **Timing Story**. Pick the active and reference laps. A negative delta means the active lap reached the same distance earlier.
2. Switch to **G–G scatter plot**. Click a point to inspect the two accelerations. Right-click the plot or use **Scatter settings** to select other channels.
3. Set X to steering and Y to throttle. Add a brake gate below 5%, then choose **Apply**. The matching sample count changes. Each plotted point still identifies its original lap and sample.
4. Choose **Open in library** to inspect that component independently. Try a different frame, then a different plot style. **Download HTML example** saves the current displayed data and renderer in one file.

To work with your own recording, open **Workbook → Open log**. You can also drop a file on the same launcher. It opens the workbook directly with the imported log. Closing the console that owns a running service stops that instance. Launch again to reopen the dashboard.

## System map

The workbook is a host for reusable HTML elements. Python prepares data from a recording or simulated lap. The element draws the result and reports picks and zoom changes to its host. An offline XY element can also filter small arrays of named channels itself.

### Stages

| Stage | Library or file | Responsibility |
| --- | --- | --- |
| Recording | CSV or Parquet | The source file stays on disk. Session time and numeric channels are the inputs. |
| Column store | Polars and PyArrow · `data_viewer/logstore.py` | Stream CSV into a reusable Parquet cache. Index row groups by time. Native Parquet enters at the indexing step. |
| Time window | PyArrow and NumPy · `Log.window` | Read the selected channel and time from overlapping groups. Keep extrema when reducing an overview. |
| XY query | PyArrow and NumPy · `data_viewer/scatter.py` | Project the needed columns, apply gates, count matches and retain bounded samples with source IDs. |
| Demo laps | NumPy · `data_viewer/telemetry.py` | Supply four reproducible laps, a circuit and sectors to the demonstration worksheets. |
| Analysis | NumPy and Plotly.py · `data_viewer/charts.py` | Calculate deltas, statistics, distributions and specialist figures from the simulated samples. |
| Inline channels | JavaScript · `projectScatter` | Read named arrays supplied to an XY element. Apply the query locally and retain original row identities. |
| Parameters | HTML attributes or a host menu | Describe the data query, axes, marks, frame and visible controls. |
| Renderer | Canvas 2D and HTML · `web/telemetry-elements.js` | Draw charts, build report tables and update instruments. Combine plot updates scheduled for the same animation frame. |
| Host event | DOM events · optional Qt WebChannel | Send the pick, visible range or menu request to the host. A native application can share one bridge across its plots. |

### Workflows

| Workflow | Route | What to observe |
| --- | --- | --- |
| Large-log scatter | Recording → Column store → XY query → Renderer | Gates evaluate original rows. The browser receives up to 3,200 points per source. |
| Time-history zoom | Recording → Column store → Time window → Renderer | An imported trace requests more detail for the selected time window. |
| Offline scatter | Parameters → Inline channels → Renderer → Host event | The HTML example can draw, zoom and pick directly from disk. |
| Demo worksheet | Demo laps → Analysis → Renderer | Each worksheet calculates the quantity appropriate to its question. |
| Appearance edit | Parameters → Renderer | Changing marker size or axis limits reuses the displayed arrays. |
| Sample pick | Renderer → Host event | The scatter selection layer repaints the marker and returns the original row ID. |

## Workbook and controls

The session and worksheet tree sit beside the central plot. The simulated session has four laps at 100 Hz. The active and reference selectors control comparisons where supported. The inspector below the worksheet shows values at the cursor. On time history, switch between elapsed time and lap distance.

| Question | Worksheet or action | Reading |
| --- | --- | --- |
| Where did I lose time? | Timing Story and sector times | Compare elapsed times at equal distance, then identify the sector contributing to the delta. |
| How did the car use grip? | G–G scatter and braking scatter | Inspect the relationship between lateral and longitudinal acceleration, optionally within a gate. |
| How often did a value occur? | Speed or suspension histogram | Read the fraction of samples in each bin. Damper velocity uses positive for bump and negative for rebound. |
| Where on the circuit? | Track report, rainbow map and GPS driving lines | Inspect sector minima, speed along the centreline or simulated positions in local coordinates. |
| What varies with frequency? | FFT and frequency response | Read the spectrum of a simulated channel or the gain and phase of the suspension-rig example. |
| Which values need exact comparison? | Statistics, sectors and acceleration reports | Read the numeric result directly from the table. |

### Inspect a plot

Click a point or focus the canvas and use the arrow keys. Left and Right step through samples; Up and Down change series. Drag horizontally to zoom. Hold Shift and drag to pan a zoomed plot. The reset control restores the full range. An imported time trace requests a new window after zoom. XY zoom operates on the currently displayed points.

Choose **Frame** for the container and **Plot style** for lines, markers, bars and grid. Fine uses thin marks, Bold increases weight, and Patterned varies the marks and grid. Switch the theme to compare contrast. The library lets you inspect the same object in isolation.

## Open a recording

Use **Workbook → Open log → Browse**, paste the local path, or drop the recording onto the launcher. Wait for the filename and sample count to appear. Select a channel and a time interval in seconds. **Full range** restores the original interval.

### File contract

CSV uses UTF-8, a comma delimiter, a decimal point and one header row with distinct numeric columns. Include finite, non-decreasing session time in `time_s` and at least one numeric channel. Continue session time across lap boundaries. Missing channel values are allowed. Include units in names when the file has no independent unit metadata.

```csv
time_s,speed_kmh,steering_deg,throttle_pct,brake_pct
0.00,83.5,-12,72,0
0.01,84.0,-10,75,0
0.02,83.8,-8,68,3
```

Parquet also needs numeric `time_s` and at least one numeric channel. Other column types are ignored. Row-group statistics let the reader reject groups outside the requested interval. For missing statistics, it reads timestamps to establish the bounds.

### What the loader does

Polars streams CSV into a temporary compressed Parquet file. The loader checks timestamps before atomically publishing the completed cache. Reopening the same unchanged CSV reuses that cache. A native Parquet recording is read in place. The cache lives in `.cache/`; it can be removed when the viewer is closed. The next CSV open then rebuilds it.

A time-history overview reads time and the selected channel. Large windows retain minima and maxima per display bin and preserve breaks for missing data. Small windows return original samples. To examine a narrower population in an XY scatter, change **From / To** or the sample gates. Imported recordings support time history and XY scatter. The specialist worksheets use the simulated session's known channel and sector definitions.

## Configure scatter

Open **Scatter settings** from the plot header, right-click the plot, or press **Shift+F10** with the canvas focused. The nine scatter worksheets use the same editor. In an imported recording, set **Plot** to **Scatter** first.

| Setting | How it affects the plot |
| --- | --- |
| X and Y channels | Choose the quantities to compare. Axis labels follow the selected channels. |
| Scale and limits | Select linear or logarithmic independently on each axis. Leave both limits blank for automatic bounds. Manual limits must increase. Log limits and displayed coordinates must be positive. |
| Sample gates | Add up to twelve conditions. A sample must pass every condition. Available comparisons are less than, at most, equal, unequal, at least and greater than. |
| Colour or size by channel | Encode another measurement per point. Density uses colour for the number of original samples per cell. |
| Shape, radius and opacity | Change the appearance of displayed points. A blank numeric field uses the current plot style. |

**Apply** commits the pending changes together. **Cancel** discards them. A channel or gate change requests a new projection. A visual-only edit reuses the displayed data. An unchanged Apply produces no new scatter request or full draw.

### Inspect throttle on corner exit

Use steering on X and throttle on Y. Add a brake gate below 5% to exclude samples with appreciable braking, then use speed for colour. This isolates low-brake samples. To identify corner exits specifically, add a phase channel or other criteria from the recording. Click a marker to inspect its values. For the simulated lap, its ID and timestamp lead back to the source.

The matching count refers to eligible original rows. The displayed count can be smaller because the scatter projection retains up to 3,200 points per source. A picked ID identifies a displayed source row. A fitted curve or bin mean is a derived value.

## Component catalogue and exports

The HTML library contains 46 elements. Choose a component and inspect its appearance, selection and zoom behaviour before embedding it. The names below take the prefix `dv-`.

| Family | Element names |
| --- | --- |
| Traces and base XY | `trace`, `history`, `scatter`, `steer-throttle`, `timing`, `outing`, `colour`, `bits` |
| Scatter analysis | `scatter-density`, `scatter-colour`, `scatter-size`, `scatter-gate`, `scatter-average`, `scatter-linear`, `scatter-polynomial` |
| Distributions and analysis | `hist`, `hist-colour`, `susp`, `susp-zones`, `susp-four`, `fft`, `frf`, `mix`, `mix-trend` |
| Maps and replay | `track`, `rainbow`, `pos`, `gps`, `race`, `rainbow-compare`, `telemetry-position`, `telemetry-gps` |
| Summary charts | `sector-chart`, `channel-chart` |
| Tables | `samples`, `sectors`, `stats`, `accel`, `status` |
| Instruments | `gauges`, `dial`, `meter`, `steering`, `gear`, `rpm`, `lamp` |

### Choose an export

**Use in HTML** shows markup for the selected element. **Download JS library** saves the shared renderer. **Download data JSON** saves the displayed payload. Serve the renderer and data beside your page when using a JSON URL. **Download HTML example** packages the displayed data, renderer and appearance into a single offline snapshot.

A snapshot contains the selected points and channels. To switch to channels that were absent at export, supply a named column store or a queryable service. In **Demos**, the engine comparisons use the same speed trace in Plotly.js, BokehJS and uPlot. Interaction demos isolate zoom, pan, picking and A/B measurement. Style demos isolate the frame using the same static trace.

## Embed a plug-in

Copy `web/telemetry-elements.js` beside your HTML and load it once. A page can host multiple chart, table and instrument tags. The host can be a desktop browser or an embedded web view. The optional example menus belong to the workbook and Qt host. Use them when they fit your application.

### Working offline example

This element plots throttle against steering and accepts only rows where brake is less than five. All arrays share the same row index. Add a stable `source` and optional `ids`, `timeChannel` or `distanceChannel` to link the selection to the original recording.

```html
<script defer src="telemetry-elements.js"></script>
<dv-scatter frame="clean" plot-style="fine" hide-tools
  query='{"x":"steer","y":"throttle","gates":[
    {"channel":"brake","op":"<","value":5}]}'
  options='{"marker":{"shape":"circle","size":3}}'>
  <script type="application/json">
    {"source":"lap:2","timeChannel":"t","channels":{
      "steer":[-18,-6,8,14],"throttle":[35,72,61,44],
      "brake":[0,8,0,2],"t":[0,0.01,0.02,0.03]}}
  </script>
</dv-scatter>
```

The inline column format is supported by `dv-scatter` and `dv-steer-throttle`. Filtering precedes sampling. Use small inline datasets for portable examples. For a large recording, give the component a data-service URL so the web view receives only the bounded result.

### Use the supplied local service

On a page served by Data Viewer, use `src="/api/scatter?source=local&amp;start=0&amp;end=120"` with the same query structure. Choose channel names that exist in the opened log. Time bounds are seconds. To load a simulated specialist figure, use a source such as `/api/scatter?view=scatter-density`. The local service must be running for those routes.

Open the [standalone scatter](../examples/plugin-scatter.html) or the [standalone histogram](../examples/histogram.html) to see the on-disk examples.

## Parameter and event reference

| Input | Contract |
| --- | --- |
| `frame`, `plot-style`, `theme` | Frames are apple, neumorphic or clean. Plot styles are fine, bold or pattern. Set light or dark explicitly or inherit the host scheme. Set height with the CSS property `--dv-height`. |
| `query` | JSON with X, Y, optional colour and size channel IDs, and an array of gates. Keys use lowercase `x`, `y`, `colour`, `size`, `gates`. Each gate has `channel`, `op`, `value`. |
| `options.axes` | `x` and `y` each accept `scale` of linear or log and a two-value numeric `range` or null for auto. |
| `options.marker` | `shape` accepts auto, circle, square, diamond or cross. `size` is a radius from 0.5 to 12 px. `opacity` is greater than zero and at most one. |
| `options.line`, `options.bar` | Lines accept width in pixels and a positive dash array, or an empty array for solid. Bars accept fill of solid, outline or pattern and a width scale greater than zero and at most one. |
| `src`, `data` | Fetch prepared JSON through a URL, embed it in a child JSON script, or assign to the element's JavaScript data property. A URL query is passed as JSON in the query parameter. |
| `hide-tools`, `external-controls` | Hide zoom buttons only, or hide the whole built-in control and readout strip. Canvas zoom, picking and events remain available. |

Prepared charts use `{data:[series], layout:{...}}`. A typical series contains `x`, `y`, `name` and `mode`. Tables use `columns`, `rows` and optional `selected`. A single instrument accepts `value`, `label` and `unit`. The composite gauge takes a sample keyed by its channels. Download a component's JSON to inspect its exact shape.

### Connect a menu once

Listen for `dv-context` and call `preventDefault()` when the host opens its own menu. Change query and appearance attributes in the same handler. The component batches them. Listen for `dv-select` to read series, index and coordinates, plus source, sample ID, time or distance where supplied. `dv-range` reports the horizontal range in axis units or null after reset.

```javascript
plot.setAttribute("query", JSON.stringify(query));
plot.setAttribute("options", JSON.stringify(options));
plot.addEventListener("dv-select", ({detail}) => inspect(detail));
```

Here `inspect` is the host's sample inspector. `plot.selectSample(source, id)` highlights a displayed source row without echoing a pick by default. `dv-load` announces accepted declarative data and `dv-error` provides an error message. Use `reload()` to refresh a URL. The optional Qt example demonstrates a native context menu, worker-thread query and two-way selection over Qt WebChannel.

## Local service and analysis

`viewer.py` serves known local assets and the API through a loopback HTTP server. The application holds one open log per service process. Windows and browser tabs connected to the same instance share that log. Each page manages its own plot configuration.

| Request | Purpose |
| --- | --- |
| GET `/api/session` | Return the application identity, catalogue, simulated laps, scatter defaults, channel labels and local request token. |
| POST `/api/open` | Open the supplied path or request the Windows picker for an empty path. Send a JSON object with `path` and the `X-Viewer-Token` header. |
| GET `/api/state` | Report import progress, cancellation, errors or ready metadata. The workbook polls while a file opens. |
| GET `/api/window` | Read one imported channel for `start`, `end` and a target bin count. Return points, matching rows and row-group count. |
| GET `/api/scatter` | Evaluate the encoded query against a simulated worksheet or the active log. For a local log supply `source=local`, `start` and `end`. |
| GET `/api/chart`, `/api/cursor` | Return a simulated worksheet or interpolated lap and reference values. Use `format=html` for portable numeric series. |
| GET `/api/demo/samples`, `/api/demo/bokeh` | Supply the demo trace or the Python-generated Bokeh example. |
| POST `/api/qt-example` | Start the bundled optional Qt example. The dashboard supplies the local request token. |

`data_viewer/telemetry.py` generates the simulated session. `charts.py` defines the catalogue and basic worksheets; `analysis_plots.py` implements specialist analyses. Plotly.py describes many figures in Python. The reusable HTML library draws its own Canvas graphics. The separate engine demos load their individual plotting runtimes.

In `web/app.js`, the workbook owns session state and cursor synchronisation. `web/scatter-host.js` implements the optional settings editor. `web/library.js` owns preview and export. The portable renderer runs independently of those files.

## Performance and evidence

Time history and XY scatter answer different questions. For time history, the loader preserves extrema in screen bins. For XY, the service counts all eligible rows and keeps a bounded deterministic sample with stable source identities. Derived statistics and specialist fits use the original eligible data where implemented. A rare XY outlier may be absent from a sampled view. Narrow the time window or gate to examine it.

| Interaction | Scatter data requests | Full plot redraws |
| --- | --- | --- |
| Edit the draft, cancel, or apply unchanged settings | 0 | 0 |
| Apply an axis or marker change | 0 | 1 |
| Apply channels, gates and appearance together | 1 | 1 |
| Pick a displayed point | 0 | 0 |

Picking restores the existing canvas and paints the selected marker. Three visual updates issued within one animation frame share one full draw. A superseded browser request is cancelled on the client and its late result is discarded. These counts were exercised by the desktop tests, including a synthetic one-million-row Parquet fixture.

### Recorded loading benchmarks

| Operation | 5 million rows | 20 million rows |
| --- | --- | --- |
| First CSV open, empty cache | 1.69 s | 9.02 s |
| Reopen cached recording, metadata only | 3.24 ms | 8.84 ms |
| First one-channel overview | 265 ms | 892 ms |
| 30-second zoom, median of five | 6.93 ms | 12.05 ms |

These are recorded backend measurements on a Windows machine with eight hardware threads and about 32 GiB of RAM. The synthetic recordings had 12 columns. Cold CSV conversion, cached metadata access, disk reads, HTTP transfer and canvas painting measure different work. The [loading study](../documentation/research/data-loading.html) describes the test conditions. The underlying [5M results](../documentation/research/benchmark.json) and [20M results](../documentation/research/benchmark-20M.json) are included.

## Repository and maintenance

| Location | Responsibility |
| --- | --- |
| `Start Data Viewer.cmd`, `viewer.py`, `requirements.txt` | Single Windows launcher, local HTTP entry point and pinned runtime packages. |
| `data_viewer/` | Python telemetry, analysis, plot construction, scatter sampling and file loading. |
| `web/` | Browser workspaces, dashboard assets and shared component library. Vendored uPlot and its licence live in `web/vendor/`. |
| `examples/` | Standalone HTML examples, style previews and the optional native Qt host. |
| `documentation/` | This Markdown source, the generated PDF and dashboard, performance studies and local reference publications. |
| `tools/` | Manual builder and reproducible data-loading benchmark. |
| `tests/` | Python unit tests and desktop checks for the dashboard, HTML library, scatter controls, exports and Qt bridge. |
| `.venv/`, `.cache/` | Local Python environment and generated Parquet cache. `PRODUCT.md` records the product brief at the repository root. |

Run these commands from the project root in PowerShell. The launcher prepares the runtime environment. Desktop browser tests use Python Playwright and Chrome. Qt tests additionally use PyQt6-WebEngine. The first browser check below takes the address printed by the running launcher.

```powershell
.\.venv\Scripts\python.exe -m unittest -v
py -3.12 tests/verify_html_library.py http://127.0.0.1:PORT
py -3.12 tests/verify_html_plugin.py
py -3.12 tests/verify_scatter_controls.py
.\.venv\Scripts\python.exe tests/verify_qt_scatter.py
```

Replace `PORT` with the actual port. For the benchmark, install the optional DuckDB and psutil packages in the project environment and run `tools/benchmark.py --rows 5000000` with that Python interpreter. Specify `--output` to save a fresh result without replacing the recorded one.

Edit `documentation/manual.md` to change the guide. With markdown-it-py and ReportLab installed, run `.\.venv\Scripts\python.exe tools/build_manual.py` to regenerate both deliverables. The viewer serves the generated files without requiring documentation-build packages at runtime.

## Troubleshooting and references

| Symptom | Action |
| --- | --- |
| The dashboard does not open | Run the single launcher from the repository. Check its console for a setup error or the actual local address. A fresh environment requires Python 3.12 and pip access. |
| An import fails | Check the extension, unique numeric CSV headers, the spelling of `time_s` and the order and finiteness of CSV timestamps. Reopen a source that changed on disk. |
| Scatter reports no samples | Check the time window, gates, finite channel values and positive coordinates on log axes. Keep the settings editor accessible while revising the gate. |
| Only a subset of XY points appears | Compare the matching count with the displayed count. Narrow the time window or query before interpreting sparse regions. |
| A plug-in shows no data or a source error | Verify the JS path and the payload for that element. A URL needs a running, reachable service. For an offline page, embed the JSON or use the exported HTML. |
| A native menu is unavailable | Browser menus and plug-ins work with the core environment. The native Qt example additionally requires PyQt6-WebEngine. |
| A recording has no sector or GPS worksheet | Use imported time histories and XY scatter. Simulated specialist worksheets rely on definitions that a generic file may not contain. |

### Examples and reference material

To try the native host, open **Dashboard → Troubleshooting and references → Open Qt example**. Right-click its scatter plot to edit the settings. If the optional dependency is missing, run `.\.venv\Scripts\python.exe -m pip install PyQt6-WebEngine` from the project root.

Open the [frame comparison](../examples/styles.html) to inspect Apple, Neumorphic and Clean against the same plots. The [interaction study](../documentation/research/interactive-plots.html) includes an A/B measurement example and the plotting-library comparison. The [MoTeC coverage index](../documentation/references/coverage.html) maps the implemented worksheet families to the locally archived manuals, help and release notes.

The project is a local prototype inspired by MoTeC i2 Pro. Hardware acquisition, licensed proprietary log import, live telemetry, synchronised video and calibration editing are outside its current scope. The desktop Qt example verifies the host contract locally. An independent viewer has to provide a compatible web view and any native event bridge it needs.
