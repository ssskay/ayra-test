import streamlit as st
import openai
import time
import requests
from io import BytesIO

# Page configuration
st.set_page_config(page_title="STEM Tutor Chatbot", page_icon="🧪")

# Get OpenAI API key from sidebar
api_key = st.sidebar.text_input("Enter your OpenAI API key:", type="password")

# Initialize the session state variables if they don't exist
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm your STEM tutor. Ask me any question about science, technology, engineering, or math."}
    ]

if "current_topic" not in st.session_state:
    st.session_state.current_topic = ""

if "generated_image" not in st.session_state:
    st.session_state.generated_image = None

if "lesson_state" not in st.session_state:
    st.session_state.lesson_state = {
        "active": False,
        "current_lesson": 0,
        "lessons_completed": False,
        "understanding_check": False
    }

# Main title
st.title("STEM Tutor Chatbot 🧪")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        
        # If this is the last assistant message and we have a generated image
        if message["role"] == "assistant" and message is st.session_state.messages[-1] and st.session_state.generated_image:
            st.image(st.session_state.generated_image, caption="Visual aid for: " + st.session_state.current_topic)

# Function to generate response word by word
def generate_response(prompt, api_key, is_understanding_check=False):
    if not api_key:
        return "Please enter your OpenAI API key in the sidebar to continue."
    
    try:
        openai.api_key = api_key
        
        # Save the current topic if this is the initial question
        if not st.session_state.lesson_state["active"]:
            st.session_state.current_topic = prompt
            st.session_state.lesson_state["active"] = True
            st.session_state.lesson_state["current_lesson"] = 1
        
        # Hardcoded responses for common STEM questions
  
        # Format system message based on whether we're teaching a lesson or checking understanding
        if st.session_state.lesson_state["active"]:
            if is_understanding_check:
                system_message = f"""You are a helpful STEM tutor. The student has just learned about {st.session_state.current_topic} (Lesson {st.session_state.lesson_state['current_lesson']-1}).
                Assess their understanding based on their response. Be encouraging but honest. Be generous with how much they explain. 
                If they understand, say 'Great understanding!' at the start of your response and then briefly summarize what they got right.
                If they don't fully understand, say 'Let's clarify:' at the start and correct any misconceptions.
                Keep your response brief and focused. At the end, ask if they're ready to continue to the next lesson."""
            else:
                # We're teaching the next lesson
                system_message = f"""You are a helpful STEM tutor teaching about {st.session_state.current_topic}.
                This is Lesson {st.session_state.lesson_state['current_lesson']} of 3 on this topic.
                Make this lesson clear, informative, and build upon any previous lessons.
                At the end of your response, ask a question to check the student's understanding of what you just taught.
                Begin your response with 'Lesson {st.session_state.lesson_state['current_lesson']}: ' followed by a subtitle."""
        else:
            # Initial response
            system_message = "You are a helpful STEM tutor. Provide clear, accurate explanations for science, technology, engineering, and mathematics topics. At the end, ask a question to check understanding."
            
        # Check for hardcoded responses only for initial queries
        if not st.session_state.lesson_state["active"] or st.session_state.lesson_state["current_lesson"] == 1:
            prompt_lower = prompt.lower()
            for key in hardcoded_responses:
                if key in prompt_lower:
                    return hardcoded_responses[key] + " Do you understand this concept? Please explain it back to me in your own words."
        
        # If no hardcoded response, use OpenAI
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            stream=True
        )
        
        # Return the streaming response object
        return response
        
    except Exception as e:
        return f"Error: {str(e)}"

# Function to generate image based on the current topic
def generate_image(topic, api_key):
    if not api_key:
        st.error("Please enter your OpenAI API key in the sidebar to generate images.")
        return None
    
    try:
        openai.api_key = api_key
        
        # Create a more descriptive prompt for DALL-E
        # General instructions that apply to all images
        general_instructions = "Create a clear, educational diagram with accurate labels. Use bright colors with good contrast. Include a title. Check all spelling carefully. Make the image look professional and realistic as if from a high-quality textbook."
        
        # Combine with topic-specific request
        image_prompt = f"{general_instructions} The topic is: {topic}."
        
        response = openai.images.generate(
            model="dall-e-3",
            prompt=image_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        
        # Get the image URL
        image_url = response.data[0].url
        
        # Download the image
        image_data = requests.get(image_url).content
        
        return BytesIO(image_data)
        
    except Exception as e:
        st.error(f"Error generating image: {str(e)}")
        return None

# Function to handle the lesson flow
def process_user_input(user_input):
    lesson_state = st.session_state.lesson_state
    
    # If we're not in an active lesson flow or we've completed all lessons
    if not lesson_state["active"] or lesson_state["lessons_completed"]:
        # Reset lesson state for a new topic
        st.session_state.lesson_state = {
            "active": False,
            "current_lesson": 0,
            "lessons_completed": False,
            "understanding_check": False
        }
        return generate_response(user_input, api_key)
    
    # If we're waiting for a student's understanding response
    if lesson_state["understanding_check"]:
        response = generate_response(user_input, api_key, is_understanding_check=True)
        lesson_state["understanding_check"] = False
        
        # Advance to next lesson
        if lesson_state["current_lesson"] < 3:
            lesson_state["current_lesson"] += 1
        else:
            lesson_state["lessons_completed"] = True
        
        return response
    
    # Otherwise, provide the next lesson
    response = generate_response(user_input, api_key)
    lesson_state["understanding_check"] = True
    return response

# Chat input
if prompt := st.chat_input("Ask a STEM question"):
    # Reset any previous images when starting a new conversation
    if not st.session_state.lesson_state["active"] or st.session_state.lesson_state["lessons_completed"]:
        st.session_state.generated_image = None
    
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.write(prompt)
    
    # Get response based on the current state of the lesson flow
    response = process_user_input(prompt)
    
    # Display assistant message
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # If response is a string (hardcoded or error message)
        if isinstance(response, str):
            # Simulate word-by-word typing for hardcoded responses
            words = response.split()
            for i, word in enumerate(words):
                full_response += word + " "
                message_placeholder.write(full_response)
                time.sleep(0.05)  # Adjust timing as needed
        else:
            # Process the streaming response from OpenAI
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    message_placeholder.write(full_response)
                    time.sleep(0.01)  # Small delay for word-by-word effect
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response.strip()})

# Visual aid button (appears after the first exchange)
if st.session_state.lesson_state["active"] and not st.session_state.generated_image:
    if st.button("Generate Visual Aid 🖼️"):
        with st.spinner("Generating visual aid..."):
            image_data = generate_image(st.session_state.current_topic, api_key)
            if image_data:
                st.session_state.generated_image = image_data
                # Force a rerun to display the image
                st.rerun()