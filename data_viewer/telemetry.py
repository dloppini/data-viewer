"""Simulated circuit session with uniformly spaced samples for time-domain analysis."""
import numpy as np

RATE = 100
SPLITS = np.array([0, .31, .66, 1.0])
LENGTH = 3400
CHANNELS = {
    "speed": ("Speed", "km/h"), "throttle": ("Throttle", "%"),
    "brake": ("Brake", "%"), "rpm": ("Engine speed", "rpm"),
    "lat": ("Lateral acceleration", "g"), "long": ("Longitudinal acceleration", "g"),
    "damper": ("Front-left damper travel", "mm"), "lambda": ("Lambda", "λ"),
    "steer": ("Steering", "°"), "gear": ("Gear", ""),
}
# Original centreline defined by a periodic spline and parameterised by arc length in metres.
PINS = np.array([[13,18],[38,17],[72,16],[84,11],[94,13],[96,23],[87,30],
                 [82,41],[67,45],[63,38],[66,31],[55,29],[45,39],[36,41],
                 [34,31],[25,28],[12,29],[7,23]], dtype=float)

def centreline():
    u = np.linspace(0, 1, 60, endpoint=False)[:, None]
    pieces = []
    for i in range(len(PINS)):
        a,b,c,d = PINS[(np.arange(i-1,i+3)) % len(PINS)]
        pieces.append(.5*((2*b)+(-a+c)*u+(2*a-5*b+4*c-d)*u**2+(-a+3*b-3*c+d)*u**3))
    xy = np.vstack([*pieces, PINS[0]])
    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]
    return arc/arc[-1]*LENGTH, (xy-xy[0])*LENGTH/arc[-1]

ARC, XY = centreline()

def position(distance):
    return np.interp(distance, ARC, XY[:,0]), np.interp(distance, ARC, XY[:,1])

def make_lap(i):
    dist = np.linspace(0, LENGTH, 6801)
    s = dist/LENGTH
    speed = 202 + 10*np.sin(2*np.pi*s)
    for j,(centre,width,loss) in enumerate([(.13,.044,96),(.27,.055,72),(.43,.041,106),
                                             (.54,.033,67),(.68,.046,85),(.83,.048,115),(.92,.020,41)]):
        offset = .004*np.sin(i*1.7+j)
        speed -= (loss+4*np.cos(i+j))*np.exp(-((s-centre-offset)/width)**2)
    speed += [-3.2, .6, 2.7, -1.4][i] + 2.8*np.sin(8*np.pi*s+i)
    times = np.r_[0,np.cumsum(np.diff(dist)*7.2/(speed[1:]+speed[:-1]))]
    # Include the finish sample for distance alignment; FFT excludes this last partial interval.
    t = np.r_[np.arange(0,times[-1],1/RATE),times[-1]]
    d = np.interp(t,times,dist)
    v = np.interp(d,dist,speed)
    acc = np.gradient(speed/3.6,times)/9.80665
    longitudinal = np.interp(d,dist,acc)
    pedal = np.clip(56+longitudinal*69+12*np.sin(2*np.pi*d/LENGTH*5+i*.16),0,100)
    brake = np.clip(-longitudinal*79-5,0,100)
    gear = np.clip(np.floor((v-38)/32)+1,1,6)
    rpm = (v*99/(.55+.45*gear))+1250
    rng = np.random.default_rng(910+i)
    lateral = (1.75-.006*v)*np.sin(2*np.pi*d/LENGTH*6+i*.06)
    angles = lateral*53+4*np.sin(t*1.9)
    damper = 12+3.3*np.sin(2*np.pi*2.4*t)+.9*np.sin(2*np.pi*9.1*t)+1.5*lateral
    return dict(t=t,d=d,speed=v,throttle=pedal,brake=brake,rpm=rpm,gear=gear,
                lat=lateral,long=longitudinal,steer=angles,damper=damper,
                **{"lambda":1.015-.00125*pedal+.012*np.sin(t*2.3)+rng.normal(0,.008,len(t))})

LAPS = [make_lap(i) for i in range(4)]

def sample(lap, distance):
    index = min(int(np.searchsorted(lap["d"],distance)),len(lap["d"])-1)
    return {k:round(float(v[index]),3) for k,v in lap.items()}

def split_times(lap):
    return np.diff(np.interp(SPLITS*LENGTH,lap["d"],lap["t"]))

def spectrum(lap):
    signal = lap["damper"][:-1]
    window = np.hanning(len(signal))
    amplitude = 2*np.abs(np.fft.rfft((signal-signal.mean())*window))/window.sum()
    return np.fft.rfftfreq(len(signal),1/RATE),amplitude

def clock(value):
    minutes, seconds = divmod(round(value*1000),60000)
    return f"{minutes}:{seconds/1000:06.3f}"
