import plotly.graph_objects as go

A,B="#2464df","#b75724"
SCALE=[[0,"#41399b"],[.25,"#3068bb"],[.5,"#188b91"],[.75,"#b58e23"],[1,"#ca512c"]]

def line(x,y,name,color=A,dash="solid"):
    return go.Scatter(x=x,y=y,name=name,mode="lines",line=dict(color=color,width=2.2,dash=dash))

def marked(x,y,name,color):
    return go.Scatter(x=x,y=y,name=name,mode="markers",marker=dict(color=color,size=10))

def axes(fig,x,y):
    fig.update_xaxes(title_text=x)
    fig.update_yaxes(title_text=y)
