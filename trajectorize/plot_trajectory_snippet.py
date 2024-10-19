
import imp
import io
import base64
import os
import kaleido
import plotly.graph_objects as go

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
                    fn=None, fv=None, fk=None, 
                    title_string="", marker_size=10,
                    top_margin=65, bottom_margin=75, right_margin=20, left_margin=20,
                    title_font_size=12,
                    theme="ggplot2"):
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
    fig.add_trace(go.Scatter(
        x=fdf[x_axis].tolist(),
        y=fdf[y_axis].tolist(), 
        mode=mode,
        marker=dict(size=marker_size),
        text=text,
        textfont=textfont,
        textposition=textposition))

    fig.update_layout(layout_spec)
    return convert_output(fig)