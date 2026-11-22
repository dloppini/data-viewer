# Data Viewer

Double-click **Start Data Viewer.cmd**. It opens the dashboard on this computer. On a fresh Windows installation the launcher sets up Python 3.12 dependencies in the project environment. You can drop a CSV or Parquet recording onto the same launcher to open it in the workbook.

Use **Workbook** to inspect a recording, **HTML library** to configure and export one of the 46 components, and **Demos** to try an individual plot or gesture. The **Dashboard** contains the interactive system map, operating guide, studies, references and optional Qt example.

## Manual

Read the [PDF manual](documentation/Data%20Viewer%20Manual.pdf), [Markdown source](documentation/manual.md) or [dashboard guide](documentation/dashboard.html). The Markdown is the source for the PDF and online guide. Both explain the user workflow, plug-in contract, data pipeline, repository layout and verification.

## Project layout

| Directory | Contents |
| --- | --- |
| `data_viewer/` | Python data loading, telemetry and analytics |
| `web/` | Workbook, library, demos and standalone HTML elements |
| `examples/` | Offline HTML examples, style previews and the native Qt host |
| `documentation/` | Manual, dashboard, research results and original MoTeC references |
| `tools/` | Manual builder and data-loading benchmark |
| `tests/` | Numerical and desktop integration checks |

Run `.\.venv\Scripts\python.exe -m unittest -v` from the project root for the numerical and server checks. To rebuild the documentation, install the optional packages in `tools/requirements-docs.txt` and run `.\.venv\Scripts\python.exe tools/build_manual.py`.
