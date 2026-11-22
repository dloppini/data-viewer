"""Analysis for the i2 catalogue. Statistics use the original samples before display reduction."""
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .plot_primitives import A, B, SCALE, axes, line, marked
from .telemetry import LAPS, LENGTH, RATE, position, split_times

ANALYSIS = {
    "scatter-density": ("Scatter", "G–G density", "Colour shows the number of original samples in each cell of a 48 × 48 G–G grid."),
    "scatter-colour": ("Scatter", "Three-channel scatter plot", "Steering angle against throttle opening, coloured by speed."),
    "scatter-size": ("Scatter", "Bubble scatter plot", "Bubble area in the G–G plot increases with brake pedal input (%)."),
    "scatter-gate": ("Scatter", "Braking scatter plot", "Only samples with more than 10% brake input are shown."),
    "scatter-average": ("Scatter", "Interval average", "Mean lambda in throttle bins five percentage points wide."),
    "scatter-linear": ("Scatter", "Linear regression", "Least-squares line fitted to all throttle and lambda samples."),
    "scatter-polynomial": ("Scatter", "Polynomial regression", "Quadratic fit to steering angle and speed across all samples."),
    "hist-colour": ("Distributions", "Two-channel histogram", "Bar height shows time in each speed bin. Colour shows mean throttle opening in that bin."),
    "susp-zones": ("Distributions", "Damper velocity zones", "Time spent in front-left bump and rebound, split at a shaft speed of 25 mm/s."),
    "susp-four": ("Distributions", "Four-corner suspension", "Compare the four simulated damper shaft velocities using the same bins and scale."),
    "frf": ("Distributions", "Frequency response", "Gain and phase between input and output on a simulated suspension rig. The H1 estimate uses overlapping Hann windows."),
    "mix-trend": ("Distributions", "Mixture trends", "Mean lambda in 250 rpm bins, with one curve per load band."),
    "bits": ("Traces", "Channel bits", "Three bits from a simulated status word show braking, full throttle and high lateral acceleration."),
    "sector-chart": ("Report charts", "Sector time trends", "Time in each sector across all four laps."),
    "channel-chart": ("Report charts", "Channel trends", "Minimum, mean and maximum speed for each lap, calculated from the time samples."),
    "rainbow-compare": ("Track", "Side-by-side rainbow maps", "Two laps share a speed scale. The markers show both cars at the same elapsed time."),
    "telemetry-position": ("Track", "Distance-based track replay", "Four simulated cars positioned on the centreline using their recorded lap distances."),
    "telemetry-gps": ("Track", "GPS track replay", "Four simulated 5 Hz GPS receivers. The cursor interpolates each car’s local east and north coordinates."),
}
COLOURS = (A, B, "#008670", "#9368ba")


def interval_mean(x, y, edges):
    counts = np.histogram(x, edges)[0]
    total = np.histogram(x, edges, weights=y)[0]
    means = np.divide(total, counts, out=np.full(len(counts), np.nan), where=counts > 0)
    return (edges[:-1] + edges[1:]) / 2, means


def frequency_response(input_signal, output_signal):
    """H1 = mean(conj(X) * Y) / mean(|X|²), phase relative to the input."""
    size = 512
    window = np.hanning(size)
    def transform(signal):
        frames = np.lib.stride_tricks.sliding_window_view(signal, size)[::size // 2]
        return np.fft.rfft((frames - frames.mean(axis=1, keepdims=True)) * window, axis=1)
    x, y = transform(input_signal), transform(output_signal)
    power = np.mean(abs(x)**2, axis=0)
    cross = np.mean(x.conj() * y, axis=0)
    h = np.divide(cross, power, out=np.full_like(cross, np.nan), where=power > power.max()*1e-8)
    return np.fft.rfftfreq(size, 1/RATE)[1:], h[1:]


def suspension_plot(key, lap):
    f = go.Figure()
    velocity = np.diff(lap["damper"][:-1])*RATE
    if key == "susp-zones":
        counts = np.histogram(velocity, [-np.inf,-25,0,25,np.inf])[0]
        labels = ["High rebound", "Low rebound", "Low bump", "High bump"]
        f.add_trace(go.Bar(x=[1,2,3,4], y=100*counts/len(velocity), name="Front-left damper", marker_color=A))
        f.update_xaxes(range=[.45,4.55], tickvals=[1,2,3,4], ticktext=labels)
        axes(f, "Damper zone (25 mm/s threshold)", "Time (%)")
    else:
        t = lap["t"][:-1]
        edges = np.arange(-160, 165, 5)
        for i, corner in enumerate(("FL","FR","RL","RR")):
            # The simulated rig uses different amplitudes and phases at each corner.
            travel = (lap["damper"][:-1] if not i else
                      12+(3.3-.25*i)*np.sin(2*np.pi*2.4*t+.55*i)
                      +(.9+.1*i)*np.sin(2*np.pi*(9.1-.4*i)*t+i)+(-1)**i*1.5*lap["lat"][:-1])
            v = np.diff(travel)*RATE
            counts = np.histogram(v, edges)[0]
            f.add_trace(line((edges[1:]+edges[:-1])/2, 100*counts/len(v), corner, COLOURS[i]))
        axes(f, "Damper shaft velocity (mm/s)", "Time (%)")
    return f


def track_plot(key, active, reference, distance):
    f = go.Figure()
    elapsed = np.interp(distance, LAPS[active]["d"], LAPS[active]["t"])
    if key == "rainbow-compare":
        f = make_subplots(rows=1, cols=2, horizontal_spacing=.035)
        laps = (LAPS[active], LAPS[reference])
        low = min(lap["speed"].min() for lap in laps)
        high = max(lap["speed"].max() for lap in laps)
        for col, (index, lap) in enumerate(zip((active,reference), laps), 1):
            x,y = position(lap["d"][::8])
            name = ("Lap " if col==1 else "Ref. ") + f"{index+1:02}"
            f.add_trace(go.Scatter(x=x, y=y, mode="markers", name=name, marker=dict(
                size=6, color=lap["speed"][::8], colorscale=SCALE, cmin=low, cmax=high,
                showscale=col==1, colorbar=dict(title="km/h"))), row=1, col=col)
            px,py = position(np.interp(elapsed, lap["t"], lap["d"]))
            f.add_trace(marked([px],[py], "", COLOURS[col-1]), row=1, col=col)
            f.update_yaxes(scaleanchor="x" if col==1 else "x2", scaleratio=1, row=1, col=col)
    else:
        x,y = position(np.linspace(0,LENGTH,500))
        f.add_trace(line(x, y, "Track", "#83919d"))
        for i,lap in enumerate(LAPS):
            # Cars have staggered starts on the same replay clock.
            at = (elapsed + i*2.5) % lap["t"][-1]
            if key == "telemetry-gps":
                ts = np.r_[lap["t"][:-1:RATE//5], lap["t"][-1]]
                d = np.interp(ts, lap["t"], lap["d"])
                east,north = position(d)
                east += (i+1)*np.sin(2*np.pi*d/LENGTH*5+i)
                north += (i+1)*np.cos(2*np.pi*d/LENGTH*3+i)
                start = max(0, at-3)
                history = np.r_[start, ts[(ts>start)&(ts<at)], at]
                f.add_trace(line(np.interp(history,ts,east), np.interp(history,ts,north), "", COLOURS[i]))
                px,py = np.interp(at,ts,east), np.interp(at,ts,north)
            else:
                px,py = position(np.interp(at, lap["t"], lap["d"]))
            f.add_trace(marked([px], [py], f"Car {i+1:02}", COLOURS[i]))
        f.update_yaxes(scaleanchor="x", scaleratio=1)
    f.update_xaxes(visible=False)
    f.update_yaxes(visible=False)
    return f


def analysis_figure(key, active, reference, distance):
    lap = LAPS[active]
    if key.startswith("susp-"):
        return suspension_plot(key, lap)
    if key in ("rainbow-compare","telemetry-position","telemetry-gps"):
        return track_plot(key, active, reference, distance)
    f = go.Figure()
    if key == "frf":
        road = np.random.default_rng(710+active).normal(size=len(lap["t"])-1)
        response = np.zeros_like(road)
        for i in range(1,len(road)):
            response[i] = .8*response[i-1] + .2*road[i]
        hz,h = frequency_response(road, response)
        f = make_subplots(rows=2, cols=1, shared_xaxes=True)
        f.add_trace(line(hz, 20*np.log10(abs(h)), "Gain"), row=1,col=1)
        f.add_trace(line(hz, np.angle(h, deg=True), "Phase", B), row=2,col=1)
        f.update_yaxes(title_text="Gain (dB)", row=1,col=1)
        f.update_yaxes(title_text="Phase (°)", row=2,col=1)
        f.update_xaxes(title_text="Frequency (Hz)", row=2,col=1)
    elif key == "bits":
        t = lap["t"]
        word = ((lap["brake"]>5).astype("uint8") | ((lap["throttle"]>=95).astype("uint8")<<1)
                | ((abs(lap["lat"])>.5).astype("uint8")<<2))
        f = make_subplots(rows=3, cols=1, shared_xaxes=True)
        for i,label in enumerate(("Brake > 5%", "Throttle ≥ 95%", "|Lateral g| > 0.5")):
            state = (word>>i)&1
            idx = np.unique(np.r_[0, np.flatnonzero(state[1:]!=state[:-1])+1, len(t)-1])
            trace = line(t[idx], state[idx], f"b{i} · {label}", COLOURS[i])
            trace.line.shape = "hv"
            f.add_trace(trace, row=i+1,col=1)
            f.update_yaxes(title_text=f"b{i}", range=[-.16,1.16], tickvals=[0,1], row=i+1,col=1)
        f.update_xaxes(title_text="Time (s)", row=3,col=1)
    elif key == "hist-colour":
        speed,throttle = lap["speed"][:-1],lap["throttle"][:-1]
        edges = np.arange(30, 246, 5)
        counts = np.histogram(speed, edges)[0]
        centres, means = interval_mean(speed, throttle, edges)
        keep = counts>0
        f.add_trace(go.Bar(x=centres[keep], y=100*counts[keep]/len(speed), width=4.5, name="Throttle",
                           marker=dict(color=means[keep], colorscale=SCALE, cmin=0, cmax=100,
                                       showscale=True, colorbar=dict(title="%"))))
        axes(f,"Speed (km/h)","Time (%)")
    elif key == "mix-trend":
        rpm,load,lam = lap["rpm"][:-1],lap["throttle"][:-1],lap["lambda"][:-1]
        edges = np.arange(np.floor(rpm.min()/250)*250, rpm.max()+250, 250)
        for i,(lo,hi) in enumerate(((0,33),(33,66),(66,101))):
            keep = (load>=lo)&(load<hi)
            x,y = interval_mean(rpm[keep],lam[keep],edges)
            trace = line(x,y,f"Load {lo}–{min(hi,100)}%",COLOURS[i])
            trace.mode = "lines+markers"
            f.add_trace(trace)
        axes(f,"Engine speed (rpm)","Lambda (λ)")
    elif key in ("sector-chart","channel-chart"):
        if key == "sector-chart":
            values = np.array([split_times(data) for data in LAPS])
            labels,unit = ("S1","S2","S3"), "Sector time (s)"
        else:
            values = np.array([[op(data["speed"][:-1]) for op in (np.min,np.mean,np.max)] for data in LAPS])
            labels,unit = ("Minimum","Mean","Maximum"), "Speed (km/h)"
        laps = np.arange(1,len(LAPS)+1)
        for i,label in enumerate(labels):
            trace = line(laps,values[:,i],label,COLOURS[i])
            trace.mode = "lines+markers"
            f.add_trace(trace)
        axes(f,"Lap",unit)
        f.update_xaxes(tickvals=laps)
    return f
