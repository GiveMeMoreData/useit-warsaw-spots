import streamlit as st
import pandas as pd
import gspread
from gspread.spreadsheet import Spreadsheet
from oauth2client.service_account import ServiceAccountCredentials
import folium
from folium import plugins


st.set_page_config(
    page_title="USEIT Warsaw",
    layout="wide",
)

def authenticate_google_sheets(credentials: dict):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials._from_parsed_json_keyfile(credentials, scope)
    client = gspread.authorize(creds)
    return client

def get_data_from_sheet(sheet_name, credentials: dict) -> pd.DataFrame:
    client = authenticate_google_sheets(credentials)
    sheet: Spreadsheet = client.open(sheet_name)
    data = pd.DataFrame(sheet.sheet1.get_all_records())
    return data


def process_data_for_render(df: pd.DataFrame) -> pd.DataFrame:
    df = df.loc[df['geometry_type'] != ""].copy()
    df['Ocena'] = df['Ocena'].astype(str).apply(lambda s: int(s) if len(s) == 1 else -1 if len(s) == 0  else int(s)/10)
    df['Latitude'] = df['Latitude'].astype(str).apply(lambda s: float(s[:2] + "." + s[2:]))
    df['Longitude'] = df['Longitude'].astype(str).apply(lambda s: float(s[:2] + "." + s[2:]))
    return df

@st.cache_data  
def filter_category(df: pd.DataFrame, filter):
    if filter != "Wszystkie":
        df = df.loc[df['Kategoria'] == filter]
    return df

@st.cache_data  
def filter_seen(df: pd.DataFrame, filter):
    if filter != "Wszystko":
        df = df.loc[df['Wizyta'] == filter]
    return df

@st.cache_data  
def filter_person(df: pd.DataFrame, filter):
    if filter != "Wszyscy":
        df = df.loc[df[f'Ocena {filter}'] != ""]
    return df

@st.cache_data  
def filter_min_score(df: pd.DataFrame, filter):
    if filter != "Wszystko":
        df = df.loc[df['Ocena'] >= filter]
    return df

@st.cache_data
def filter_map(df: pd.DataFrame, category_filter, person_filter, seen_filter, min_score_filter) -> pd.DataFrame:
    df = filter_category(df, category_filter)
    df = filter_seen(df, seen_filter)
    df = filter_person(df, person_filter)
    df = filter_min_score(df, min_score_filter)
    return df


# Function to display a folium map
def plot_map(df):
    m = folium.Map(location=[df['Latitude'].median(), df['Longitude'].median()], zoom_start=10)
    plugins.Fullscreen(
        position="topright",
        title="Expand me",
        title_cancel="Exit me",
        force_separate_button=True,
    ).add_to(m)

    for _, row in df.iterrows():
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=folium.Popup(f"<b>Nazwa:</b> {row['Nazwa']}<br><b>Kategoria:</b> {row['Kategoria']}<br><b>Ocena:</b> {row['Ocena']}<br><b>Google Map ", max_width=300),
            icon=folium.Icon(color="blue")
        ).add_to(m)
    
    return m

# Main Streamlit app
def main():

    st.session_state.reload = True
    cols = st.columns(5)

    # Session state to track whether data needs to be reloaded
    if 'reload' not in st.session_state:
        st.session_state.reload = False
        
    df = st.session_state.get('data', None)
    if df is None:
        # Load configuration
        sheet_name = st.secrets['config']['sheet_name']
        credentials = st.secrets['credentials']

        df = get_data_from_sheet(sheet_name, credentials)
        df = process_data_for_render(df)
        st.session_state['data'] = df


    # Reload the data when the button is pressed
    if cols[0].button("Reload Data"):
        st.session_state.reload = True

    if st.session_state.reload:
       
        categories = []
        # Add category filter
        categories = df['Kategoria'].unique().tolist()
        categories.insert(0, "Wszystkie")  # Option to show all categories
        people = ["Wszyscy", 'Bartek', 'Iga', 'Zosia', 'Asia', 'Herki', 'Wojtek', 'Bogna', 'Dominik']
        seen = ["Wszystko","Tak", "Planowana", "Nie"]
        category_filter = cols[1].selectbox("Kategoria", categories)
        person_filter = cols[2].selectbox("Osoba", people)
        seen_filter = cols[3].selectbox("Odwiedzone", seen)
        min_score_filter = cols[4].selectbox("Ocena minimalna", ['Wszystko', 1 ,2, 3, 4, 5])

        df_filtered = filter_map(df, category_filter, person_filter, seen_filter, min_score_filter)

        # Show map
        map_object = plot_map(df_filtered)

        # Using folium.Figure for better integration with Streamlit
        folium_map = folium.Figure(title="Locations Map with Filters")
        folium_map.add_child(map_object)

        # st.map(df_filtered, latitude="Latitude", longitude="Longitude", size="Ocena")
        st.components.v1.html(folium_map._repr_html_(), height = 1080)

        # Reset the reload flag after reloading the data
        st.session_state.reload = False

if __name__ == "__main__":
    main()
