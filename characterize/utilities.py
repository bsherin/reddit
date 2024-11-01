import json
import collections
import six
import nltk
import pandas as pd

def flatten(l):
    return [item for sublist in l for item in sublist]

def flatten_and_truncate(l, maxlen):
    return [item for sublist in l for item in sublist[:maxlen]]

def ds(text):
    print(text)

def save_to_json(struc, path):
    with open(path, "w") as f:
        json.dump(struc, f)

def iterable(arg):
    return (
        isinstance(arg, collections.abc.Iterable)
        and not isinstance(arg, six.string_types)
    )

def convert_df_to_datalist(df, max_rows=None, include_row_labels=False):
    if max_rows is not None:
        new_df = df.head(max_rows)
    else:
        new_df = df
    if not include_row_labels:
        columns = list(new_df.columns)
        mat = new_df.to_numpy()
        res = [columns] + mat.tolist()
    else:
        res = [["label"] + list(new_df.columns)]
        for label, s in new_df.iterrows():
            res.append([label] + s.tolist())
    return res

def html_table(data, title=None, click_type="word-clickable", sortable=True,
                sidebyside=False, has_header=True, max_rows=100, header_style=None, body_style=None,
                column_order=None, include_row_labels=True, outer_border=False):
    show_header = has_header

    if isinstance(data, pd.DataFrame):
        if column_order is not None:
            df = data.reindex(columns=column_order)
        else:
            df = data
        dlist = convert_df_to_datalist(df, max_rows, include_row_labels=include_row_labels)
        show_header = True
    elif isinstance(data, list) and isinstance(data[0], dict):
        df = pd.DataFrame(data)
        if column_order is not None:
            df = df.reindex(columns=column_order)
        dlist = convert_df_to_datalist(df, max_rows, include_row_labels=include_row_labels)
        show_header = True
    elif isinstance(data, nltk.FreqDist):
        if max_rows is None:
            nrows = 100
        else:
            nrows = max_rows
        dlist = [["word", "freq"]] + data.most_common(nrows)
        show_header = True
    elif isinstance(data, dict):
        dlist = [["key", "value"]]
        for key, the_val in data.items():
            dlist.append([key, the_val])
        dlist = dlist[:max_rows]
        show_header = True
    elif isinstance(data, list):
        dlist = data[:max_rows]
    elif isinstance(data, pd.Series):
        ddict = dict(data)
        dlist = [["key", "value"]]
        for n, key, the_val in enumerate(ddict.items()):
            if n > max_rows:
                break
            dlist.append([key, the_val])
        show_header = True
    else:
        dlist = data
    return build_html_table_from_data_list(dlist, title, click_type, sortable, sidebyside,
                                           show_header, header_style, body_style, outer_border, max_rows=max_rows)

def build_html_table_from_data_list(data_list, title=None, click_type="word-clickable",
                                    sortable=True, sidebyside=False, has_header=True,
                                    header_style=None, body_style=None, outer_border=False, max_rows=100):

    base_class_string = "bp5-html-table bp5-html-table-bordered bp5-html-table-condensed bp5-html-table-striped bp5-small html-table"
    if outer_border:
        base_class_string += " html-table-bordered"
    if header_style is None:
        hstyle = "{}"
    else:
        hstyle = header_style
    if body_style is None:
        bstyle = "font-size:13px"
    else:
        bstyle = body_style
    if sortable:
        if not sidebyside:
            the_html = u"<table class='{} fw-table sortable'>".format(base_class_string)
        else:
            the_html = u"<table class='{} sidebyside-table sortable'>".format(base_class_string)
    else:
        if not sidebyside:
            the_html = u"<table class='{} fw-table'>".format(base_class_string)
        else:
            the_html = u"<table class='{} sidebyside-table'>".format(base_class_string)

    if title is not None:
        the_html += u"<caption>{0}</caption>".format(title)
    if has_header:
        the_html += u"<thead><tr>"
        if iterable(data_list[0]):
            for c in data_list[0]:
                the_html += u"<th style='{1}'>{0}</th>".format(c, hstyle)
        else:
            the_html += u"<th style='{1}'>{0}</th>".format(data_list[0], hstyle)
        the_html += u"</tr></thead>"
        start_from = 1
    else:
        start_from = 0
    the_html += u"<tbody>"

    for rnum, r in enumerate(data_list[start_from:][:max_rows]):
        if click_type == u"row-clickable":
            the_html += u"<tr class='row-clickable'>"
            if iterable(r):
                for c in r:
                    the_html += u"<td style='{1}'>{0}</td>".format(c, bstyle)
            else:
                the_html += u"<td style='{1}'>{0}</td>".format(r, bstyle)
            the_html += u"</tr>"
        elif click_type == u"word-clickable":
            the_html += u"<tr>"
            if iterable(r):
                for c in r:
                    the_html += u"<td class='word-clickable' style='{1}'>{0}</td>".format(c, bstyle)
            else:
                the_html += u"<td class='word-clickable' style='{1}'>{0}</td>".format(r, bstyle)
            the_html += u"</tr>"
        else:
            the_html += u"<tr>"
            if iterable(r):
                for cnum, c in enumerate(r):
                    the_html += "<td class='element-clickable' data-row='{1}' style='{3}' " \
                                "data-col='{2}' data-val='{0}'>{0}</td>".format(c, str(rnum), str(cnum), bstyle)
            else:
                the_html += "<td class='element-clickable' data-row='{1}' style='{3}' " \
                            "data-col='{2}' data-val='{0}'>{0}</td>".format(r, str(rnum), str(0), bstyle)
            the_html += "</tr>"
    
    style_html =  """
            <style>
                .sidebyside-table {
                    vertical-align: top;
                    margin-top: 25px;
                    margin-bottom: 25px;
                    margin-right: 20px;
                }
            </style>
        """
    
    return style_html + the_html