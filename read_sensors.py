# -*- coding: utf-8 -*-
"""
Created on Sun Jan 16 09:00:01 2022

@author: martimy
"""

import pandas as pd
import influxdb
import streamlit as st


@st.cache(allow_output_mutation=True)
def load_dataframe(host, dbname, user, password):
    port = 8086

    query = 'SELECT temperature, pressure, humidity, batteryVoltage, mac '\
            'FROM "ruuvi_measurements" '\
            'WHERE ("source" = \'maenrp3\') AND time >= now() - 12h fill(null);'

    client = influxdb.InfluxDBClient(
        host, port, user, password, dbname, ssl=True, verify_ssl=False)
    return pd.DataFrame(client.query(query, chunked=True, chunk_size=100000).get_points())


st.title('Sensor View')
st.write('This app reads and displays environmental sensors data from InfluxDB time-series database.')

dbname = st.secrets["DB_NAME"]
host = st.secrets["HOST_NAME"]
user = st.secrets["db_creds"]["username"]
password = st.secrets["db_creds"]["password"]


data_load_state = st.text('Loading data...')
df = load_dataframe(host, dbname, user, password)
data_load_state.text("Data loading done!")

# Convert InfluxDB time to Pandas time index
df["Datetime"] = pd.to_datetime(df["time"])
#df["Datetime"] = df["Datetime"].dt.tz_convert("America/Halifax")
df = df.set_index('Datetime')
df = df.drop(['time'], axis=1)

# Show raw data
if st.checkbox('Show raw data'):
    st.subheader('Raw Data')
    # st.write(df)  # General
    st.dataframe(df)  # Specific

# Select sensors
macs = df.mac.unique()
sensors = st.multiselect('Select a Sensor', macs)

# Filter the data by sensor and take the average of 5min
lst = {s: df.loc[df.mac == s].resample('5T').mean() for s in sensors}

if lst:
    st.header('Current Readings')
    for key in lst:
        item = lst[key]
        col0, col1, col2, col3 = st.columns(4)
        col0.write(f"Sensor: {key}")
        col1.metric("Temperature",
                    f'{item["temperature"].iloc[-1]:.0f} \N{DEGREE SIGN}C')
        col2.metric("Humidity", f'{item["humidity"].iloc[-1]:.0f} %')
        col3.metric("Pressure", f'{item["pressure"].iloc[-1]:.0f} hPa')

    st.header('Historical Readings')

    st.subheader('Temperature')
    temper_list = [lst[key]["temperature"] for key in lst]
    temper_data = pd.concat(temper_list, axis=1, keys=sensors)
    st.line_chart(temper_data)

    st.subheader('Humidity')
    humid_list = [lst[key]["humidity"] for key in lst]
    humid_data = pd.concat(humid_list, axis=1, keys=sensors)
    st.line_chart(humid_data)

    st.subheader('Pressure')
    press_list = [lst[key]["pressure"] for key in lst]
    press_data = pd.concat(press_list, axis=1, keys=sensors)
    st.line_chart(press_data)

else:
    st.write('No sensor selected!')
