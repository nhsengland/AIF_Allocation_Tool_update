# -------------------------------------------------------------------------
# Copyright (c) 2021 NHS England and NHS Improvement. All rights reserved.
# Licensed under the MIT License. See license.txt in the project root for
# license information.
# -------------------------------------------------------------------------

"""
FILE:           dashboard.py
DESCRIPTION:    streamlit weighted capitation tool
USAGE:
CONTRIBUTORS:   
CONTACT:        
CREATED:        2021
VERSION:        0.0.2
"""

# Libraries
# -------------------------------------------------------------------------
# python
import json
import time
import base64
import utils

# 3rd party:
import streamlit as st
import pandas as pd

# Set default place in session
# -----------------------------------------------------
if "Group 1" not in st.session_state:
    st.session_state["Group 1"] = {
        "gps": [
            "A83005: Whinfield Medical Practice",
            "A83013: Neasham Road Surgery",
            "A83034: Blacketts Medical Practice",
        ],
        "ics": "Cumbria and North East",
    }
if "places" not in st.session_state:
    st.session_state.places = ["Group 1"]

# Functions & Calls
# -------------------------------------------------------------------------
# aggregate on a query and set of aggregations
def aggregate(data, query, name, on, aggregations):
    df = data.query(query)
    if on not in df.columns:
        df.insert(loc=0, column=on, value=name)
    df_group = df.groupby(on).agg(aggregations)
    df_group = df_group.astype(int)
    return df, df_group


# calculate index of weighted populations
def get_index(place_indices, ics_indices, index_names, index_numerator):
    ics_indices[index_names] = ics_indices[index_numerator].div(
        ics_indices["GP pop"].values, axis=0
    )
    place_indices[index_names] = (
        place_indices[index_numerator]
        .div(place_indices["GP pop"].values, axis=0)
        .div(ics_indices[index_names].values, axis=0)
    )
    return place_indices, ics_indices


def render_svg(svg):
    """Renders the given svg string."""
    b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    html = r'<img src="data:image/svg+xml;base64,%s"/>' % b64
    st.write(html, unsafe_allow_html=True)


# Download functionality
@st.cache
def convert_df(df):
    return df.to_csv(index=False).encode("utf-8")


aggregations = {
    "GP pop": "sum",
    "Weighted G&A pop": "sum",
    "Weighted Community pop": "sum",
    "Weighted Mental Health pop": "sum",
    "Weighted Maternity pop": "sum",
    "Weighted HCHS pop": "sum",
    "Weighted Market Forces Factor pop": "sum",
    "Weighted EACA pop": "sum",
    "Weighted Prescribing pop": "sum",
    "Weighted AM pop": "sum",
    "Target exc remote (£k)": "sum",
    "Target inc remote (£k)": "sum",
    "Overall Weighted pop": "sum",
}

index_numerator = [
    "Weighted G&A pop",
    "Weighted Community pop",
    "Weighted Mental Health pop",
    "Weighted Maternity pop",
    "Weighted HCHS pop",
    "Weighted Market Forces Factor pop",
    "Weighted EACA pop",
    "Weighted Prescribing pop",
    "Weighted AM pop",
    "Overall Weighted pop",
]

index_names = [
    "G&A Index",
    "Community Index",
    "Mental Health Index",
    "Maternity Index",
    "HCHS Index",
    "Market Forces Factor Index",
    "EACA Index",
    "Prescribing Index",
    "AM Index",
    "Overall Index",
]

gp_query = "practice_display == @place_state"
ics_query = "`ICS name` == @ics_state"  # escape column names with backticks https://stackoverflow.com/a/56157729

# Markdown
# -----------------------------------------------------
st.markdown("PROTOTYPE UNDER DEVELOPMENT - Last Updated 14th December 2021")

# NHS Logo
svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 16">
            <path d="M0 0h40v16H0z" fill="#005EB8"></path>
            <path d="M3.9 1.5h4.4l2.6 9h.1l1.8-9h3.3l-2.8 13H9l-2.7-9h-.1l-1.8 9H1.1M17.3 1.5h3.6l-1 4.9h4L25 1.5h3.5l-2.7 13h-3.5l1.1-5.6h-4.1l-1.2 5.6h-3.4M37.7 4.4c-.7-.3-1.6-.6-2.9-.6-1.4 0-2.5.2-2.5 1.3 0 1.8 5.1 1.2 5.1 5.1 0 3.6-3.3 4.5-6.4 4.5-1.3 0-2.9-.3-4-.7l.8-2.7c.7.4 2.1.7 3.2.7s2.8-.2 2.8-1.5c0-2.1-5.1-1.3-5.1-5 0-3.4 2.9-4.4 5.8-4.4 1.6 0 3.1.2 4 .6" fill="white"></path>
          </svg>
"""
render_svg(svg)

st.title("ICS Place Based Allocation Tool")

instructions = st.checkbox("Show Instructions")
if instructions:
    st.markdown(
        "This tool is designed to allow place, for allocation purposes, to be defined by aggregating GP Practices within an ICS. Please refer to the User Guide for instructions."
    )
    st.markdown(
        "The Relative Need Index for ICS (i) and Defined Place (p) is given by the formula:"
    )
    st.latex(r""" (WP_p/GP_p)\over (WP_i/GP_i)""")
    st.markdown(
        "This tool utilises weighted populations calculated from the 2018/19 GP Registered Practice Populations"
    )

# Import Data
# -----------------------------------------------------
data = utils.get_data()
ics = utils.get_sidebar(data)

# SIDEBAR
# -----------------------------------------------------
ics_choice = st.sidebar.selectbox("Select your ICS:", ics, help="Select an ICS")
ccg_filter = st.sidebar.checkbox("Filter by CCG")
if ccg_filter:
    ccg = data["CCG name"].loc[data["ICS name"] == ics_choice].unique().tolist()
    ccg_choice = st.sidebar.selectbox("Select your CCG:", ccg, help="Select a CCG")
    practices = list(data["practice_display"].loc[data["CCG name"] == ccg_choice])
else:
    practices = list(data["practice_display"].loc[data["ICS name"] == ics_choice])

practice_choice = st.sidebar.multiselect(
    "Select practices",
    practices,
    help="Select GP Practices to aggregate into a single defined 'place'",
)
place_name = st.sidebar.text_input(
    "Name your Group", "Group 1", help="Give your defined place a name to identify it"
)
if st.sidebar.button("Save Group", help="Save group to session state", key="output",):
    if [place_name] not in st.session_state:
        st.session_state[place_name] = {"gps": practice_choice, "ics": ics_choice}
    if "places" not in st.session_state:
        st.session_state.places = [place_name]
    if place_name not in st.session_state.places:
        st.session_state.places = st.session_state.places + [place_name]

# if st.sidebar.button("Reset Group", key="output"):
#    del st.session_state[place_name]
#    st.session_state.places = st.session_state.places

session_state_dict = dict.fromkeys(st.session_state.places, [])
for key, value in session_state_dict.items():
    session_state_dict[key] = st.session_state[key]
session_state_dict["places"] = st.session_state.places

session_state_dump = json.dumps(session_state_dict, indent=4, sort_keys=False)

st.sidebar.write("-" * 34)  # horizontal separator line.

# Use file uploaded to read in groups of practices
advanced_options = st.sidebar.checkbox("Advanced Options")
if advanced_options:
    # downloads
    st.sidebar.download_button(
        label="Download session data as JSON",
        data=session_state_dump,
        file_name="session.json",
        mime="text/json",
    )
    # uploads
    form = st.sidebar.form(key="my-form")
    group_file = form.file_uploader(
        "Upload previous session data as JSON", type=["json"]
    )
    submit = form.form_submit_button("Submit")
    if submit:
        if group_file is not None:
            my_bar = st.progress(0)
            for percent_complete in range(100):
                time.sleep(0.01)
                my_bar.progress(percent_complete + 1)
            d = json.load(group_file)
            st.session_state.places = d["places"]
            for place in d["places"]:
                st.session_state[place] = d[place]

debug = st.sidebar.checkbox("Show Session State")
if debug:
    st.markdown("DEBUGGING")
    st.session_state


# BODY
# -----------------------------------------------------
option = st.selectbox("Select Group", (st.session_state.places))

st.info("**Selected GP Practices: **" + str(st.session_state[option]["gps"]))

st.subheader("Group Metrics")
st.write(
    "KPIs shows the Need Indices of **",
    option,
    "** compared to the **",
    st.session_state[option]["ics"],
    " ICS** average",
)

# Write session state values to query vars
place_state = st.session_state[option]["gps"]
ics_state = st.session_state[option]["ics"]

# get place aggregations
place_query, place_indices = aggregate(
    data, gp_query, option, "Place Name", aggregations
)

# get ICS aggregations
ics_query1, ics_indices = aggregate(
    data, ics_query, st.session_state[option]["ics"], "ICS name", aggregations
)

# index calcs
place_indices1, ics_indices1 = get_index(
    place_indices, ics_indices, index_names, index_numerator
)
# print all data
ics_indices1.insert(loc=0, column="Group / ICS", value=st.session_state[option]["ics"])
place_indices1.insert(loc=0, column="Group / ICS", value=option)
df_print = pd.concat(
    [ics_indices1, place_indices1], axis=0, join="inner", ignore_index=True
)

# tbd: Loop this
(Overall, GA, Community, MentalHealth, Maternity) = st.columns(5)
with Overall:
    place_metric = round(place_indices1["Overall Index"][0].astype(float), 3)
    ics_metric = round(ics_indices1["Overall Index"][0].astype(float) - place_metric, 3)
    st.metric(
        "Overall Index", place_metric, ics_metric, delta_color="normal",
    )
with GA:
    place_metric = round(place_indices1["G&A Index"][0].astype(float), 3)
    ics_metric = round(ics_indices1["G&A Index"][0].astype(float) - place_metric, 3)
    st.metric(
        "G&A Index", place_metric, ics_metric, delta_color="normal",
    )
with Community:
    place_metric = round(place_indices1["Community Index"][0].astype(float), 3)
    ics_metric = round(
        ics_indices1["Community Index"][0].astype(float) - place_metric, 3
    )
    st.metric(
        "Community Index", place_metric, ics_metric, delta_color="normal",
    )
with MentalHealth:
    place_metric = round(place_indices1["Mental Health Index"][0].astype(float), 3)
    ics_metric = round(
        ics_indices1["Mental Health Index"][0].astype(float) - place_metric, 3
    )
    st.metric(
        "Mental Health Index", place_metric, ics_metric, delta_color="normal",
    )
with Maternity:
    place_metric = round(place_indices1["Maternity Index"][0].astype(float), 3)
    ics_metric = round(
        ics_indices1["Maternity Index"][0].astype(float) - place_metric, 3
    )
    st.metric(
        "Maternity Index", place_metric, ics_metric, delta_color="normal",
    )
# add these
(HCHS, MarketForcesFactor, EACA, Prescribing, AM) = st.columns(5)
with HCHS:
    place_metric = round(place_indices1["HCHS Index"][0].astype(float), 3)
    ics_metric = round(ics_indices1["HCHS Index"][0].astype(float) - place_metric, 3)
    st.metric(
        "HCHS Index", place_metric, ics_metric, delta_color="normal",
    )
with MarketForcesFactor:
    place_metric = round(
        place_indices1["Market Forces Factor Index"][0].astype(float), 3
    )
    ics_metric = round(
        ics_indices1["Market Forces Factor Index"][0].astype(float) - place_metric, 3
    )
    st.metric(
        "MFF Index", place_metric, ics_metric, delta_color="normal",
    )
with EACA:
    place_metric = round(place_indices1["EACA Index"][0].astype(float), 3)
    ics_metric = round(ics_indices1["EACA Index"][0].astype(float) - place_metric, 3)
    st.metric(
        "EACA Index", place_metric, ics_metric, delta_color="normal",
    )
with Prescribing:
    place_metric = round(place_indices1["Prescribing Index"][0].astype(float), 3)
    ics_metric = round(
        ics_indices1["Prescribing Index"][0].astype(float) - place_metric, 3
    )
    st.metric(
        "Prescribing Index", place_metric, ics_metric, delta_color="normal",
    )
with AM:
    place_metric = round(place_indices1["AM Index"][0].astype(float), 3)
    ics_metric = round(ics_indices1["AM Index"][0].astype(float) - place_metric, 3)
    st.metric(
        "AM Index", place_metric, ics_metric, delta_color="normal",
    )

st.subheader("Downloads")

print_table = st.checkbox("Preview data download")
if print_table:
    with st.container():
        utils.write_table(df_print)

csv = convert_df(df_print)
st.download_button(
    label="Download {place} data as CSV".format(place=option),
    data=csv,
    file_name="{place} place based allocations.csv".format(place=option),
    mime="text/csv",
)
