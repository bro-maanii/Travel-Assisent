import json
import time
import streamlit as st
import plotly.graph_objects as go
from openai import OpenAI


# Preconditions

st.set_page_config(
    page_title="Travel Guider",
    page_icon="🗺️",
    layout="wide",
)

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

assistant_id = st.secrets["ASSISTANT_ID"]
assistant_state = "assistant"
thread_state = "thread"
conversation_state = "conversation"
last_openai_run_state = "last_openai_run"
map_state = "map"
markers_state = "markers"


# SESSION STATE SETUP

if (assistant_state not in st.session_state) or (thread_state not in st.session_state):
    st.session_state[assistant_state] = client.beta.assistants.retrieve(assistant_id)
    st.session_state[thread_state] = client.beta.threads.create()

if conversation_state not in st.session_state:
    st.session_state[conversation_state] = []

if last_openai_run_state not in st.session_state:
    st.session_state[last_openai_run_state] = None

if map_state not in st.session_state:
    st.session_state[map_state] = {
        "latitude": 30.3753,
        "longitude": 69.3451,
        "zoom": 14,
    }

if markers_state not in st.session_state:
    st.session_state[markers_state] = None

# TOOLS SETUP

def update_map_state(latitude, longitude, zoom):
    """OpenAI tool to update map
    """
    st.session_state[map_state] = {
        "latitude": latitude,
        "longitude": longitude,
        "zoom": zoom,
    }
    return "Map updated"


def add_markers_state(latitudes, longitudes, labels):
    """OpenAI tool to update markers
    """
    st.session_state[markers_state] = {
        "lat": latitudes,
        "lon": longitudes,
        "text": labels,
    }
    return "Markers added"


tool_to_function = {
    "update_map": update_map_state,
    "add_markers": add_markers_state,
}

def get_assistant_id():
    return st.session_state[assistant_state].id


def get_thread_id():
    return st.session_state[thread_state].id


def get_run_id():
    return st.session_state[last_openai_run_state].id


def Result_Click(destination,budget,travel_dates,interests,travel_style,transportation_preference,cuisine_preferences,special_requirements):
    # mark the markers as None
    st.session_state[markers_state]=None
    # user-content
    st.session_state.userkey= f'''Give your best sugustions to help me plan my trip. Following are the details:
    Desired Destination: {destination}, 
    Budget: {budget} $,
    Preferred Travel Dates: {travel_dates},
    Interests: {interests},
    CultureAccommodation Preference: {travel_style},
    Travel Style: {travel_style},
    Transportation Preference: {transportation_preference},
    Cuisine Preferences: {cuisine_preferences},
    Special Requirements: {special_requirements} Also mark all the places carefully to the map with a marker. And also give informative comments about the places.'''
    
    client.beta.threads.messages.create(
        thread_id=get_thread_id(),
        role="user",
        content= st.session_state.userkey
    )
    st.session_state[last_openai_run_state] = client.beta.threads.runs.create(
        assistant_id=get_assistant_id(),
        thread_id=get_thread_id(),
    )

    completed = False

    # Polling
    with st.spinner("Computing Assistant answer"):
        time.sleep(6)
        
        while not completed:
            run = client.beta.threads.runs.retrieve(
                thread_id=get_thread_id(),
                run_id=get_run_id(),
            )

            if run.status == "requires_action":
                tools_output = []
                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    f = tool_call.function
                    f_name = f.name
                    f_args = json.loads(f.arguments)
                    tool_result = tool_to_function[f_name](**f_args)
                    tools_output.append(
                        {
                            "tool_call_id": tool_call.id,
                            "output": tool_result,
                        }
                    )
   
                client.beta.threads.runs.submit_tool_outputs(
                    thread_id=get_thread_id(),
                    run_id=get_run_id(),
                    tool_outputs=tools_output,
                )

            if run.status == "completed":
                
                completed = True

            else:
                time.sleep(0.1)

    st.session_state[conversation_state] = [
        (m.role, m.content[0].text.value)
        for m in client.beta.threads.messages.list(get_thread_id()).data
    ]
def clear_chat():
    with st.spinner(text="Clearing chat..."):
        # Delete the thread
        st.session_state[thread_state] = client.beta.threads.delete(
            thread_id=get_thread_id()
        )
        # mark the markers as None
        st.session_state[markers_state]=None
        # create a new thread
        st.session_state[thread_state] = client.beta.threads.create()
        # Create a new thread
        st.session_state[conversation_state]=[]

    st.success("Chat Cleared!")

def display_message(role, content):
    if role == "user":
        return 
    elif role == "assistant":
        with st.container():
            st.image("AI_icon.png", width=30 ,caption="AI")
            st.success(content)
        

# UI-SETUP

st.title(" AI Travel Assistant 🗺️✈️ ")
st.info("Hello and welcome to your personal travel assistant powered by OpenAI! To get started, please provide your details below, and I'll assist you in planning your journey. Whether it's booking flights, finding accommodations, or suggesting exciting destinations, I'm here to help make your travel experience seamless and enjoyable.")

left_col, right_col = st.columns(2)
with left_col:
    with st.container(height=500):
        destination = st.text_input("Your Desired Destination:")
        budget = st.number_input("Select the Budget Range (in USD):")
        travel_dates = st.date_input("Preferred Travel Dates:")
        interests = st.multiselect("Your Interests:", ["Beaches", "Mountains", "History", "Adventure", "Culture"])
        travel_style = st.radio("Travel Style:", ["Relaxing", "Adventurous", "Cultural Exploration"])
        transportation_preference = st.selectbox("Transportation Preference:", ["Flying", "Driving", "Public Transportation"])
        cuisine_preferences = st.multiselect("Cuisine Preferences:", ["Local", "International", "Vegetarian"])
        special_requirements = st.text_area("Special Requirements:")
        # button
        st.button("Submit",on_click=Result_Click, args=(destination,budget,travel_dates,interests,travel_style,transportation_preference,cuisine_preferences,special_requirements,))
    
with right_col:
    with st.container(height=500):
        st.markdown(
            "#### Result:"
        )
        with right_col:
            st.button("Delete Chat",on_click=clear_chat) 
        for role, message in st.session_state[conversation_state]:
            display_message(role, message)

with st.container():
    fig = go.Figure(
        go.Scattermapbox(
            mode="markers",
        )
    )
    if st.session_state[markers_state] is not None:
        fig.add_trace(
            go.Scattermapbox(
                mode="markers",
                marker=go.scattermapbox.Marker(
                    size=20,
                    color="red",
                ),
                lat=st.session_state[markers_state]["lat"],
                lon=st.session_state[markers_state]["lon"],
                text=st.session_state[markers_state]["text"],
            )
        )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        mapbox=dict(
            accesstoken=st.secrets["MAPBOX_TOKEN"],
            center=go.layout.mapbox.Center(
                lat=st.session_state[map_state]["latitude"],
                lon=st.session_state[map_state]["longitude"],
            ),
            pitch=0,
            zoom=st.session_state[map_state]["zoom"],
        ),
        
    )
    st.plotly_chart(
        fig, config={"displayModeBar": False}, use_container_width=True, key="plotly"
    )

