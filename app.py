import streamlit as st
from dotenv import load_dotenv
import os
import time

from google import genai

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    IpBlocked,
    RequestBlocked,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    AgeRestricted
)

from urllib.parse import urlparse, parse_qs


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="YouTube Video Summarizer",
    page_icon="📹",
    layout="centered"
)


# ============================================================
# LOAD .ENV FILE
# ============================================================

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")


# ============================================================
# CHECK API KEY
# ============================================================

if not API_KEY:

    st.error("⚠️ Google API Key is missing!")

    st.info(
        "Please check your .env file and make sure it contains "
        "GOOGLE_API_KEY."
    )

    st.stop()


# ============================================================
# CREATE GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=API_KEY
)


# ============================================================
# APPLICATION TITLE
# ============================================================

st.title("📹 YouTube Video Summary Creator")

st.write(
    "Enter a YouTube video link and generate "
    "AI-powered detailed notes."
)


# ============================================================
# FUNCTION 1:
# EXTRACT YOUTUBE VIDEO ID
# ============================================================

def extract_video_id(url):

    try:

        parsed_url = urlparse(url)

        # ----------------------------------------------------
        # Normal YouTube URL
        # Example:
        # https://www.youtube.com/watch?v=ABC123
        # ----------------------------------------------------

        if "youtube.com" in parsed_url.netloc:

            # Normal watch URL
            if parsed_url.path == "/watch":

                video_id = parse_qs(
                    parsed_url.query
                ).get("v", [None])[0]

                return video_id

            # YouTube Shorts URL
            if "/shorts/" in parsed_url.path:

                video_id = (
                    parsed_url.path
                    .split("/shorts/")[1]
                    .split("/")[0]
                )

                return video_id

            # YouTube Embed URL
            if "/embed/" in parsed_url.path:

                video_id = (
                    parsed_url.path
                    .split("/embed/")[1]
                    .split("/")[0]
                )

                return video_id


        # ----------------------------------------------------
        # Short YouTube URL
        # Example:
        # https://youtu.be/ABC123
        # ----------------------------------------------------

        elif "youtu.be" in parsed_url.netloc:

            video_id = (
                parsed_url.path
                .lstrip("/")
                .split("/")[0]
            )

            return video_id


        # ----------------------------------------------------
        # Invalid URL
        # ----------------------------------------------------

        return None


    except Exception:

        return None


# ============================================================
# FUNCTION 2:
# FETCH YOUTUBE TRANSCRIPT
# ============================================================

def extract_transcript_details(video_id):

    try:

        # ----------------------------------------------------
        # Create YouTube Transcript API object
        # ----------------------------------------------------

        ytt_api = YouTubeTranscriptApi()


        # ----------------------------------------------------
        # Fetch transcript
        # English is preferred
        # ----------------------------------------------------

        transcript_data = ytt_api.fetch(
            video_id,
            languages=["en"]
        )


        # ----------------------------------------------------
        # Convert transcript objects into text
        # ----------------------------------------------------

        transcript = " ".join(
            item.text
            for item in transcript_data
        )


        # ----------------------------------------------------
        # Check empty transcript
        # ----------------------------------------------------

        if not transcript.strip():

            return (
                "Error fetching transcript: "
                "The transcript is empty."
            )


        return transcript


    # --------------------------------------------------------
    # YOUTUBE IP BLOCK
    # --------------------------------------------------------

    except IpBlocked:

        return (
            "Error fetching transcript: "
            "YouTube has blocked the IP address used by "
            "this application. Please wait and try again later."
        )


    # --------------------------------------------------------
    # YOUTUBE REQUEST BLOCK
    # --------------------------------------------------------

    except RequestBlocked:

        return (
            "Error fetching transcript: "
            "YouTube blocked the transcript request. "
            "Please wait and try again later."
        )


    # --------------------------------------------------------
    # TRANSCRIPTS DISABLED
    # --------------------------------------------------------

    except TranscriptsDisabled:

        return (
            "Error fetching transcript: "
            "This video does not have transcripts enabled."
        )


    # --------------------------------------------------------
    # NO TRANSCRIPT FOUND
    # --------------------------------------------------------

    except NoTranscriptFound:

        return (
            "Error fetching transcript: "
            "No English transcript was found for this video."
        )


    # --------------------------------------------------------
    # VIDEO UNAVAILABLE
    # --------------------------------------------------------

    except VideoUnavailable:

        return (
            "Error fetching transcript: "
            "This YouTube video is unavailable."
        )


    # --------------------------------------------------------
    # AGE RESTRICTED VIDEO
    # --------------------------------------------------------

    except AgeRestricted:

        return (
            "Error fetching transcript: "
            "This video is age restricted and its transcript "
            "could not be retrieved."
        )


    # --------------------------------------------------------
    # OTHER ERRORS
    # --------------------------------------------------------

    except Exception as e:

        return (
            f"Error fetching transcript: {str(e)}"
        )


# ============================================================
# FUNCTION 3:
# GENERATE GEMINI SUMMARY
# ============================================================

def generate_gemini_content(transcript_text):

    prompt = """
You are an expert YouTube video summarizer.

Analyze the YouTube transcript provided below.

Create detailed and easy-to-understand notes.

Use the following format:

# Topic Name

# Channel Name
If the channel name is available from the transcript.
If it is not available, write:
"Not available in transcript."

# 1. Introduction

Give a short explanation of what the video is about.

# 2. Important Key Points

List the most important points from the video.

Use bullet points.

# 3. Main Concepts

Explain the important concepts discussed in the video.

Use simple English.

# 4. Important Examples

Mention important examples given in the video.

# 5. Important Information

Mention useful facts, steps, methods, definitions,
or explanations from the video.

# 6. Final Conclusion

Give a short conclusion of the video.

IMPORTANT RULES:

- Use simple English.
- Make the notes useful for a college student.
- Use headings and bullet points.
- Do not invent information.
- Only use information present in the transcript.
- Keep the answer approximately 400-500 words.

Here is the transcript:

"""


    # ========================================================
    # GEMINI MODELS
    # ========================================================

    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash"
    ]


    last_error = None


    # ========================================================
    # TRY MODELS
    # ========================================================

    for model_name in models_to_try:

        try:

            with st.spinner(
                f"🤖 Gemini is generating your summary using {model_name}..."
            ):

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt + transcript_text
                )


            # ------------------------------------------------
            # CHECK RESPONSE
            # ------------------------------------------------

            if response.text:

                return response.text


            last_error = (
                f"{model_name} returned an empty response."
            )


        except Exception as e:

            last_error = str(e)


            # ------------------------------------------------
            # TEMPORARY GEMINI ERROR
            # ------------------------------------------------

            if (
                "503" in str(e)
                or "UNAVAILABLE" in str(e)
                or "high demand" in str(e).lower()
            ):

                # Try next model
                time.sleep(1)

                continue


            # ------------------------------------------------
            # OTHER GEMINI ERROR
            # ------------------------------------------------

            return (
                f"Error generating summary: {str(e)}"
            )


    # ========================================================
    # ALL MODELS FAILED
    # ========================================================

    return (
        "Error generating summary: "
        "Gemini is temporarily unavailable or experiencing "
        "high demand. Please try again after a short time.\n\n"
        f"Last error: {last_error}"
    )


# ============================================================
# YOUTUBE URL INPUT
# ============================================================

youtube_link = st.text_input(
    "🔗 Enter YouTube Video Link:",
    placeholder="https://www.youtube.com/watch?v=..."
)


# ============================================================
# SHOW VIDEO THUMBNAIL
# ============================================================

if youtube_link:

    video_id = extract_video_id(youtube_link)

    if video_id:

        thumbnail_url = (
            f"https://img.youtube.com/vi/{video_id}/0.jpg"
        )

        st.image(
            thumbnail_url,
            caption="YouTube Video",
            use_container_width=True
        )

    else:

        st.error(
            "⚠️ Invalid YouTube URL. "
            "Please enter a valid YouTube link."
        )


# ============================================================
# SUMMARY BUTTON
# ============================================================

if st.button(
    "📝 Get Summary",
    use_container_width=True
):

    # ========================================================
    # CHECK URL
    # ========================================================

    if not youtube_link:

        st.error(
            "⚠️ Please enter a YouTube video link."
        )


    else:

        # ====================================================
        # EXTRACT VIDEO ID
        # ====================================================

        video_id = extract_video_id(
            youtube_link
        )


        if not video_id:

            st.error(
                "⚠️ Could not extract YouTube video ID."
            )


        else:

            # =================================================
            # FETCH TRANSCRIPT
            # =================================================

            with st.spinner(
                "🔄 Fetching YouTube transcript..."
            ):

                transcript_text = (
                    extract_transcript_details(
                        video_id
                    )
                )


            # =================================================
            # CHECK TRANSCRIPT
            # =================================================

            if transcript_text.startswith(
                "Error fetching transcript:"
            ):

                st.error(
                    transcript_text
                )


            else:

                st.success(
                    "✅ Transcript fetched successfully!"
                )


                # =============================================
                # GENERATE SUMMARY
                # =============================================

                summary = (
                    generate_gemini_content(
                        transcript_text
                    )
                )


                # =============================================
                # CHECK SUMMARY
                # =============================================

                if summary.startswith(
                    "Error generating summary:"
                ):

                    st.error(
                        summary
                    )


                else:

                    # =========================================
                    # DISPLAY SUMMARY
                    # =========================================

                    st.success(
                        "✅ Summary generated successfully!"
                    )

                    st.markdown(
                        "## 📝 Detailed Notes"
                    )

                    st.markdown(
                        summary
                    )


                    # =========================================
                    # SHOW ORIGINAL TRANSCRIPT
                    # =========================================

                    with st.expander(
                        "📜 View Original Transcript"
                    ):

                        st.write(
                            transcript_text
                        )