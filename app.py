import streamlit as st
from google import genai
import json

# ----------------------------
# 🔹 Configure your AI client
# ----------------------------
API_KEY = "AIzaSyAX7YFEeb7wLW5I3VsZG3nMLmXY5A71164"  # Replace with your Gemini API key
client = genai.Client(api_key=API_KEY)

# ----------------------------
# 🔹 Initialize session state
# ----------------------------
if "step" not in st.session_state:
    st.session_state.step = 1
if "questions" not in st.session_state:
    st.session_state.questions = []
if "user_answers" not in st.session_state:
    st.session_state.user_answers = []
if "evaluation" not in st.session_state:
    st.session_state.evaluation = []

# ----------------------------
# 🔹 STEP 1 — User Inputs
# ----------------------------
if st.session_state.step == 1:
    st.markdown("<h1 style='text-align: center; color: #4B0082;'>🤖 AI Interview Simulator</h1>", unsafe_allow_html=True)
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        role = st.text_input("Job Role", placeholder="e.g. Python Developer")
        company = st.text_input("Company (optional)", placeholder="e.g. Google")
    with col2:
        topic = st.text_input("Topic", placeholder="e.g. Data Structures")
        experience = st.selectbox("Experience Level", ["Fresher", "1-3 years", "3-5 years", "5+ years"])

    num_questions = st.slider("Number of Questions", 1, 15, 5)

    if st.button("Generate Questions"):
        if not role or not topic:
            st.error("❌ Please enter both a Job Role and a Topic.")
        else:
            with st.spinner("⏳ Generating questions from AI…"):
                # 🔹 Distribute difficulty based on number of questions
                difficulties = []
                for i in range(num_questions):
                    if i < num_questions // 3:
                        difficulties.append("Easy")
                    elif i < 2 * num_questions // 3:
                        difficulties.append("Medium")
                    else:
                        difficulties.append("Hard")

                # Construct prompt with per-question difficulty
                prompt_q = f"Generate {num_questions} interview questions for a {role} applying to {company} for a {experience} position about {topic}. "
                prompt_q += "Make the first questions easy, the middle ones medium, and the last ones hard. Only list the questions numbered 1 to {num_questions}, without answers.\n"

                try:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt_q
                    )
                    # Parse questions
                    text = response.text.strip()
                    lines = text.split("\n")
                    questions = [line.strip() for line in lines if line.strip()]
                    st.session_state.questions = questions
                    st.session_state.step = 2
                    st.stop()  # replaces experimental_rerun
                except Exception as e:
                    st.error(f"⚠️ AI Error: {e}")

# ----------------------------
# 🔹 STEP 2 — Answer Questions
# ----------------------------
elif st.session_state.step == 2:
    st.markdown("<h2 style='text-align: center; color: #4B0082;'>📝 Answer the Questions</h2>", unsafe_allow_html=True)
    st.markdown("Provide your answers below. Try to answer as completely as possible.")
    st.markdown("---")

    # Initialize answers if not already
    if "user_answers" not in st.session_state or len(st.session_state.user_answers) != len(st.session_state.questions):
        st.session_state.user_answers = [""] * len(st.session_state.questions)

    # Display questions with text areas
    for idx, q in enumerate(st.session_state.questions):
        st.markdown(f"**{q}**")
        st.session_state.user_answers[idx] = st.text_area(
            f"Your answer for Question {idx+1}",
            value=st.session_state.user_answers[idx],
            key=f"ans_{idx}"
        )

    if st.button("Submit Answers"):
        st.session_state.step = 3
        st.stop()

# ----------------------------
# 🔹 STEP 3 — AI Evaluation & Overall Pass Probability
# ----------------------------
elif st.session_state.step == 3:
    st.markdown("<h2 style='text-align: center; color: #4B0082;'>📊 Interview Evaluation</h2>", unsafe_allow_html=True)
    st.markdown("Your answers have been evaluated by AI. See feedback and scores below.")
    st.markdown("---")

    eval_resp = None  # Initialize to avoid NameError

    with st.spinner("🧠 Evaluating answers…"):
        try:
            # Build evaluation prompt
            eval_prompt = """You are a professional interview evaluator. Evaluate the user's answers honestly and accurately.
Do not sugarcoat feedback; point out mistakes clearly and professionally.
For each question, return a JSON object with:
- question: the question text
- score: 0 to 100
- feedback: detailed professional evaluation
Return a JSON list containing all questions only, without extra text.\n\n"""

            for q, a in zip(st.session_state.questions, st.session_state.user_answers):
                eval_prompt += f"Question: {q}\nUserAnswer: {a}\n\n"

            # Call AI
            eval_resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=eval_prompt
            )

            # ----------------------------
            # Extract JSON safely
            # ----------------------------
            import re, json
            text = eval_resp.text.strip()
            json_match = re.search(r'\[.*\]', text, re.DOTALL)  # extract JSON array
            if json_match:
                results = json.loads(json_match.group())
            else:
                st.warning("⚠️ Could not parse AI evaluation. See raw output:")
                st.code(text)
                results = []

            # Store evaluation in session state
            st.session_state.evaluation = results

        except Exception as e:
            st.warning("⚠️ AI evaluation failed:")
            if eval_resp is not None:
                st.code(eval_resp.text)
            else:
                st.code(str(e))
            results = []

    # ----------------------------
    # Display Results
    # ----------------------------
    if results:
        for idx, r in enumerate(results):
            st.markdown(f"### 📌 Q{idx+1}: {r.get('question','')}")
            st.info(f"**Your Score:** {r.get('score',0)}/100")
            st.success(f"**Feedback:** {r.get('feedback','No feedback')}")
            st.markdown("---")

        # Overall pass probability
        scores = [q.get("score", 0) for q in results]
        overall_prob = sum(scores) / len(scores)
        st.markdown(f"<h3 style='text-align: center; color: #006400;'>🏆 Overall Interview Pass Probability: {overall_prob:.2f}%</h3>", unsafe_allow_html=True)

    # Restart button
    if st.button("Restart Interview"):
        st.session_state.step = 1
        st.session_state.questions = []
        st.session_state.user_answers = []
        st.session_state.evaluation = []
        st.stop()