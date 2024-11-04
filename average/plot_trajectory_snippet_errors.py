import matplotlib as mpl
from matplotlib.colors import rgb2hex
import copy
import plotly.graph_objects as go

import imp
import plotly.io as pio
import io
import base64
import os
import kaleido

def get_col_types(pdf):
    col_types = {}
    for k in pdf.iloc[0].keys():
        col_types[k] = type(pdf.iloc[0][k])
    return col_types

def convert_output(fig):

    buf = io.BytesIO()
    fig.write_image(buf, format='svg')  # Set format as 'svg'
    buf.seek(0)
    data_uri = base64.b64encode(buf.read()).decode('utf-8')
    img_tag = f'<img style="width: 100%" src="data:image/svg+xml;base64,{data_uri}" alt="Plotly Image"/>'
    return img_tag
    
def plot_trajectory(df, x_axis, y_axis, 
                    width=1000, height=500, 
                    fn=None, fv=None, fk=None, xstrings=None,
                    show_errors=False, fit_curve=False, frac=0.1, error_bar_thickness=1,
                    title_string="", marker_size=10, fit_line_color="green", fit_line_thickness=4,
                    error_bar_color="red", marker_color="blue",
                    top_margin=65, bottom_margin=75, right_margin=20, left_margin=20,
                    title_font_size=12, theme="ggplot2"):
    filtered_df = df.copy(deep=True)
    col_types = get_col_types(df)
    for col, typ in col_types.items():
        try:
            filtered_df[col] = filtered_df[col].astype(typ)
        except:
            filtered_df[col] = filtered_df[col].astype(str)
            print(f"Column {col} recast to string")
    if fn is not None:
        print("got a filter")
        if fn in col_types:
            fv = col_types[fn](fv)
        if fk == "==":
            filtered_df = filtered_df[filtered_df[fn] == fv]
        elif fk == "<=":
            filtered_df = filtered_df[filtered_df[fn] <= fv]
        else:
            print('filtering greater than or equal')
            filtered_df = filtered_df[filtered_df[fn] >= fv]
        filter_string = (f"<b>{fn}</b>:{fk}{fv}")
        filter_summary_string = (f"{fn}:{fk}{fv}")
        
    fig = go.Figure()
    
    layout_spec = {
        "height": height,
        "width": width,
        "template": theme,
        "xaxis": {"title": x_axis},
        "yaxis": {"title": y_axis},
        "margin": {
            "t": top_margin, 
            "b": bottom_margin, 
            "r": right_margin,
            "l": left_margin
        },
    }

    tstring = title_string
    summary = f"{y_axis} v. {x_axis}"
    if fn is not None:
        tstring += "<br>" + filter_string
        summary += " " + filter_summary_string

    layout_spec["title"] = {
        "text": tstring, 
        "font": {"size": title_font_size},
    }

    tlist_unique = [None]
    fdf = filtered_df
    mode = "markers"
    text = None
    textposition = None
    textfont = None
    if show_errors:
        print("got show errors true")
        fig.add_trace(go.Scatter(
            x=fdf[x_axis].tolist(),
            y=fdf[y_axis].tolist(), 
            mode=mode,
            marker=dict(size=marker_size, color=marker_color),
            name="scores",
            text=text,
            textfont=textfont,
            textposition=textposition,
            error_y=dict(
                type='data',
                array=fdf["std_dev"].tolist(),
                visible=True,
                color=error_bar_color,
                thickness=error_bar_thickness
            )
        ))
    else:
        print("got show errors false")
        fig.add_trace(go.Scatter(
            x=fdf[x_axis].tolist(),
            y=fdf[y_axis].tolist(), 
            mode=mode,
            marker=dict(size=marker_size, color=marker_color),
            text=text,
            textfont=textfont,
            textposition=textposition))
    if fit_curve:
        print("got fit curve true")
        import statsmodels.api as sm
        x_values = fdf[x_axis].tolist()
        y_values = fdf[y_axis].tolist()
        lowess = sm.nonparametric.lowess(y_values, x_values, frac=frac) # frac is the fraction of data used for smoothing
        # Extracting smoothed data
        lowess_x = lowess[:, 0]
        lowess_y = lowess[:, 1]
        fig.add_trace(go.Scatter(
            x=lowess_x,
            y=lowess_y,
            mode='lines',
            name='LOWESS Fit',
            line=dict(color=fit_line_color, width=fit_line_thickness)
        ))
    if xstrings is not None:
        tickvals = [t[0] for t in xstrings]
        ticktext = [t[1] for t in xstrings]
        fig.update_xaxes(
            tickmode='array',
            tickvals=tickvals,
            ticktext=ticktext
        )
    fig.update_layout(layout_spec)
    return convert_output(fig)