import os
import json
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from google import genai
from dotenv import load_dotenv

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="VoC Insight Engine | GenAI Academy",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INITIALIZATION ---
load_dotenv()
ENV_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize session state for API key tracking
if 'user_provided_api_key' not in st.session_state:
    st.session_state.user_provided_api_key = None
if 'using_fallback_key' not in st.session_state:
    st.session_state.using_fallback_key = False

# --- CACHING & STATE MANAGEMENT ---
# Initialize session state variables to prevent data loss on UI refresh
if 'selected_product' not in st.session_state:
    st.session_state.selected_product = None
if 'insights' not in st.session_state:
    st.session_state.insights = None
if 'action_plan' not in st.session_state:
    st.session_state.action_plan = None
if 'insights_cache' not in st.session_state:
    st.session_state.insights_cache = {}  # Cache: {product_name: {insights, action_plan}}
if 'current_file_id' not in st.session_state:
    st.session_state.current_file_id = None  # Track which file is loaded

def get_file_hash(uploaded_file):
    """Generate a simple hash to identify the uploaded file."""
    if uploaded_file is None:
        return None
    # Use name and size to create a unique identifier for the file
    return f"{uploaded_file.name}_{uploaded_file.size}"

def reset_state():
    """Clears the AI insights when a new product is selected."""
    st.session_state.insights = None
    st.session_state.action_plan = None

def clear_cache_for_new_file():
    """Clears all cached insights when a new CSV file is uploaded."""
    st.session_state.insights_cache = {}
    st.session_state.insights = None
    st.session_state.action_plan = None
    st.session_state.selected_product = None

def get_cached_insights(product_name):
    """Retrieve cached insights for a specific product."""
    return st.session_state.insights_cache.get(product_name, {}).get('insights')

def get_cached_action_plan(product_name):
    """Retrieve cached action plan for a specific product."""
    return st.session_state.insights_cache.get(product_name, {}).get('action_plan')

def cache_insights(product_name, insights, action_plan):
    """Cache insights and action plan for a specific product."""
    if product_name not in st.session_state.insights_cache:
        st.session_state.insights_cache[product_name] = {}
    st.session_state.insights_cache[product_name]['insights'] = insights
    st.session_state.insights_cache[product_name]['action_plan'] = action_plan

@st.cache_data(show_spinner=False)
def load_data(file_or_path):
    """Caches the loaded CSV so Pandas doesn't re-read it constantly."""
    return pd.read_csv(file_or_path)

# --- SAMPLE DATA GENERATOR (MULTI-PRODUCT) ---
SAMPLE_CSV_DATA = """review_id,product_id,product_name,rating,review_date,review_text
1,P101,AeroBrew Smart Mug,5,2026-03-01,Absolutely love it! Keeps my coffee hot for hours. The battery life is surprisingly good.
2,P101,AeroBrew Smart Mug,2,2026-03-05,"The temperature control is great, but the companion app keeps crashing on my Android phone."
3,P101,AeroBrew Smart Mug,4,2026-03-10,"Solid mug. The matte black finish looks premium. However, the lid is a bit difficult to clean."
4,P101,AeroBrew Smart Mug,1,2026-03-12,Complete waste of money. The charging coaster stopped working after two weeks.
5,P202,Lumina Desk Lamp,5,2026-03-02,Perfect lighting for my home office. The dimming feature is incredibly smooth.
6,P202,Lumina Desk Lamp,4,2026-03-08,"Great lamp, very bright. The base is a little wobbly though."
7,P303,SoundWave Earbuds,3,2026-03-15,"Audio quality is decent, but the left earbud disconnects randomly."
8,P303,SoundWave Earbuds,2,2026-03-18,They hurt my ears after 30 minutes. The active noise cancellation is basically non-existent.
9,P303,SoundWave Earbuds,1,2026-03-20,Microphone is terrible. No one can hear me on calls. Do not buy."""

# =====================================================================
# --- AI AGENTS ---
# =====================================================================

def run_agent_1_extraction(reviews_text, product_name):
    """Agent 1: Extracts structured JSON data from raw reviews."""
    prompt = f"""
    You are an expert E-commerce Product Manager. Analyze the following customer reviews for the product: '{product_name}'.
    
    Extract actionable insights and return a strict JSON object with this exact schema:
    {{
        "overall_sentiment_score": <float between 1.0 and 10.0 representing qualitative satisfaction>,
        "executive_summary": "<A concise 2-sentence summary of the product's current state>",
        "top_flaws": [
            {{"issue": "<brief name of flaw>", "frequency_mention": "<brief evidence from text>"}}
        ],
        "top_praised_features": [
            {{"feature": "<brief name of feature>", "reason": "<why users like it>"}}
        ]
    }}

    Raw Customer Reviews:
    {reviews_text}
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"temperature": 0.2, "response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        return {"error": str(e)}

def run_agent_2_strategy(flaws_json, product_name):
    """Agent 2: Drafts an action plan based on the extracted flaws."""
    prompt = f"""
    You are the Lead Engineer for '{product_name}'.
    Look at the following product flaws extracted from recent customer reviews by our AI system.
    
    Draft a concise, 3-step immediate action plan for the engineering and QA teams to resolve these issues.
    Do not use generic advice. Be specific to the flaws provided. Format the output in clean Markdown.

    Product Flaws:
    {json.dumps(flaws_json, indent=2)}
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"temperature": 0.4}
        )
        return response.text
    except Exception as e:
        return f"Error generating action plan: {e}"

# =====================================================================
# --- UI & DASHBOARD ---
# =====================================================================

st.title("📊 Voice of Customer (VoC) Insight Engine")
st.markdown("Automate product strategy by instantly converting raw customer reviews into actionable engineering insights.")
st.divider()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔐 API Configuration")
    
    # API Key Input with Info Icon
    col_api, col_info = st.columns([4, 1])
    with col_api:
        user_api_key = st.text_input(
            "Enter your Gemini API Key:",
            type="password",
            placeholder="Your API key here...",
            help="Get your free API key at https://aistudio.google.com/app/apikey"
        )
    
    # Determine which API key to use
    if user_api_key:
        GEMINI_API_KEY = user_api_key
        st.session_state.user_provided_api_key = user_api_key
        st.session_state.using_fallback_key = False
        st.success("✅ Using your provided API key")
    elif ENV_API_KEY:
        GEMINI_API_KEY = ENV_API_KEY
        st.session_state.using_fallback_key = True
        st.warning(
            "⚠️ **Limited Free-Tier Usage**\n\n"
            "Using the fallback API key from .env file. This is subject to strict free-tier rate limits.\n\n"
            "**Recommendation:** Enter your own Gemini API key above for:\n"
            "• Higher rate limits\n"
            "• Better reliability\n"
            "• Uninterrupted analysis\n\n"
            "[Get your free API key](https://aistudio.google.com/app/apikey)"
        )
    else:
        st.error("❌ No API Key Found\n\nPlease either:\n1. Enter your Gemini API key above, or\n2. Set GEMINI_API_KEY in your .env file")
        GEMINI_API_KEY = None
    
    st.markdown("---")
    st.header("1. Data Ingestion")
    st.download_button(
        label="📄 Download Multi-Product Template",
        data=SAMPLE_CSV_DATA,
        file_name="voc_multiproduct_template.csv",
        mime="text/csv",
        help="Use this format to upload thousands of reviews across multiple products."
    )
    st.markdown("---")
    uploaded_file = st.file_uploader("Upload your reviews (CSV)", type="csv")
    
    # Track file changes and clear cache if a new file is uploaded
    current_file_id = get_file_hash(uploaded_file)
    if current_file_id != st.session_state.current_file_id:
        if current_file_id is not None:  # Only clear if a file is actually uploaded
            clear_cache_for_new_file()
        st.session_state.current_file_id = current_file_id

# --- MAIN WORKFLOW ---
if GEMINI_API_KEY is None:
    st.error("❌ Cannot proceed without an API key. Please configure your API key in the sidebar.")
    st.stop()

# Initialize client with the selected API key
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    st.error(f"❌ Failed to initialize API client: {e}")
    st.stop()

if uploaded_file is not None:
    # 1. Load Data
    df = load_data(uploaded_file)
    
    # Ensure necessary columns exist
    if 'product_name' not in df.columns or 'rating' not in df.columns or 'review_text' not in df.columns:
        st.error("CSV must contain 'product_name', 'rating', and 'review_text' columns.")
        st.stop()

    # 2. Product Selection (On-Demand Filtering)
    products = df['product_name'].unique().tolist()
    
    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        selected_product = st.selectbox(
            "2. Select a Product to Analyze:", 
            options=products,
            on_change=reset_state,  # Clears session state if user switches products
            key="product_selector"
        )
    
    # Load cached insights if available for the selected product
    cached_insights = get_cached_insights(selected_product)
    cached_action_plan = get_cached_action_plan(selected_product)
    
    if cached_insights is not None and cached_action_plan is not None:
        st.session_state.insights = cached_insights
        st.session_state.action_plan = cached_action_plan
    
    # 3. Filter DataFrame
    prod_df = df[df['product_name'] == selected_product]
    
    # 4. Standard Metrics & Visualizations (Pandas + Plotly)
    # 4. Standard Metrics & Visualizations
    st.subheader(f"Data Overview: {selected_product}")
    
    total_reviews = len(prod_df)
    avg_rating = prod_df['rating'].mean()
    
    # --- DATE RANGE ---
    prod_df['review_date'] = pd.to_datetime(prod_df['review_date'])
    min_date = prod_df['review_date'].min().strftime('%b %d, %Y')
    max_date = prod_df['review_date'].max().strftime('%b %d, %Y')
    st.caption(f"📅 **Date Range Analyzed:** {min_date} — {max_date}")
    st.write("")
    
    # Layout: Rating Card on the left, Trend Line on the right
    col_card, col_trend = st.columns([1, 2])
    
    with col_card:
        # 1. Calculate metrics dynamically for the SELECTED product
        total_reviews = len(prod_df)
        avg_rating = prod_df['rating'].mean() if total_reviews > 0 else 0
        
        rating_counts = prod_df['rating'].value_counts().to_dict()
        tot = max(total_reviews, 1) 
        
        # Grab the raw counts
        c5 = rating_counts.get(5, 0)
        c4 = rating_counts.get(4, 0)
        c3 = rating_counts.get(3, 0)
        c2 = rating_counts.get(2, 0)
        c1 = rating_counts.get(1, 0)

        # Calculate the percentages for the bar widths
        p5 = (c5 / tot) * 100
        p4 = (c4 / tot) * 100
        p3 = (c3 / tot) * 100
        p2 = (c2 / tot) * 100
        p1 = (c1 / tot) * 100

        # 2. HTML Card (Added a right-aligned span for the counts at the end of each row)
        html_card = f"""
<div style="background-color: #1E1F26; border-radius: 20px; padding: 25px; width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.1); font-family: sans-serif; color: white;">
<h4 style="text-align: center; margin-top: 0; margin-bottom: 15px; font-weight: 500; color: #FFFFFF;">Rating and Reviews</h4>
<div style="text-align: center; margin-bottom: 25px;">
<span style="font-size: 3.2rem; font-weight: bold;">{avg_rating:.1f}</span>
<span style="font-size: 2.2rem; color: #FFB400; vertical-align: top; margin-left: 5px;">⭐</span>
<p style="color: #9E9E9E; margin: 0; font-size: 0.9rem;">{total_reviews} ratings</p>
</div>
<div style="display: flex; flex-direction: column; gap: 10px;">
<div style="display: flex; align-items: center; gap: 15px;"><span style="font-weight: bold; font-size: 0.9rem; width: 10px;">5</span><div style="background-color: #EEEEEE; border-radius: 10px; flex-grow: 1; height: 10px;"><div style="background-color: #FFB400; width: {p5}%; height: 100%; border-radius: 10px;"></div></div><span style="font-size: 0.9rem; color: #9E9E9E; width: 25px; text-align: right;">{c5}</span></div>
<div style="display: flex; align-items: center; gap: 15px;"><span style="font-weight: bold; font-size: 0.9rem; width: 10px;">4</span><div style="background-color: #EEEEEE; border-radius: 10px; flex-grow: 1; height: 10px;"><div style="background-color: #FFB400; width: {p4}%; height: 100%; border-radius: 10px;"></div></div><span style="font-size: 0.9rem; color: #9E9E9E; width: 25px; text-align: right;">{c4}</span></div>
<div style="display: flex; align-items: center; gap: 15px;"><span style="font-weight: bold; font-size: 0.9rem; width: 10px;">3</span><div style="background-color: #EEEEEE; border-radius: 10px; flex-grow: 1; height: 10px;"><div style="background-color: #FFB400; width: {p3}%; height: 100%; border-radius: 10px;"></div></div><span style="font-size: 0.9rem; color: #9E9E9E; width: 25px; text-align: right;">{c3}</span></div>
<div style="display: flex; align-items: center; gap: 15px;"><span style="font-weight: bold; font-size: 0.9rem; width: 10px;">2</span><div style="background-color: #EEEEEE; border-radius: 10px; flex-grow: 1; height: 10px;"><div style="background-color: #FFB400; width: {p2}%; height: 100%; border-radius: 10px;"></div></div><span style="font-size: 0.9rem; color: #9E9E9E; width: 25px; text-align: right;">{c2}</span></div>
<div style="display: flex; align-items: center; gap: 15px;"><span style="font-weight: bold; font-size: 0.9rem; width: 10px;">1</span><div style="background-color: #EEEEEE; border-radius: 10px; flex-grow: 1; height: 10px;"><div style="background-color: #FFB400; width: {p1}%; height: 100%; border-radius: 10px;"></div></div><span style="font-size: 0.9rem; color: #9E9E9E; width: 25px; text-align: right;">{c1}</span></div>
</div>
</div>
"""
        st.markdown(html_card, unsafe_allow_html=True)

    with col_trend:
        prod_df['review_date'] = pd.to_datetime(prod_df['review_date'])

        st.write("") 
        # --- WEEKLY TREND ANALYSIS ---
        trend_df = prod_df.groupby(pd.Grouper(key='review_date', freq='W'))['rating'].mean().reset_index()
        trend_df.rename(columns={'review_date':'review week'}, inplace = True)
        trend_df = trend_df.dropna()
        
        fig_trend = px.line(
            trend_df, 
            x='review week', 
            y='rating', 
            markers=True, 
            line_shape='spline', 
            title="Average Rating Trend (Weekly)"
        )
        
        fig_trend.update_layout(
            yaxis_range=[0.5, 5.5], 
            yaxis_title="Avg Star Rating",
            xaxis_title="",
            height=280, # Matched height to align nicely with the HTML card
            margin=dict(l=0, r=0, t=40, b=0),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        fig_trend.update_traces(line_color='#FFB400', marker=dict(size=8, color='#FFB400'))
        st.plotly_chart(fig_trend, use_container_width=True, config={'displayModeBar': False})

    st.divider()

    # --- AI PIPELINE EXECUTION ---
    with col_btn:
        st.write("") # Spacing
        st.write("")
        
        # Show status if insights are cached
        if cached_insights is not None:
            st.caption("✅ Cached")
        
        if st.button("🧠 Generate AI Insights", type="primary", use_container_width=True):
            reset_state() # Clear previous runs
            
            with st.spinner("Agent 1: Extracting insights..."):
                # Compile text for prompt
                combined_reviews = "\n".join([f"Rating: {row['rating']}/5. Text: {row['review_text']}" for _, row in prod_df.iterrows()])
                
                # Execute Agent 1
                st.session_state.insights = run_agent_1_extraction(combined_reviews, selected_product)
            
            if "error" not in st.session_state.insights and st.session_state.insights.get("top_flaws"):
                with st.spinner("Agent 2: Drafting engineering strategy..."):
                    # Execute Agent 2
                    st.session_state.action_plan = run_agent_2_strategy(st.session_state.insights["top_flaws"], selected_product)
            
            # Cache the generated insights for this product
            if st.session_state.insights and "error" not in st.session_state.insights:
                cache_insights(selected_product, st.session_state.insights, st.session_state.action_plan)

    # --- RENDER AI INSIGHTS (From Session State) ---
    if st.session_state.insights is not None:
        if "error" in st.session_state.insights:
            st.error(f"Error generating insights: {st.session_state.insights['error']}")
        else:
            insights = st.session_state.insights
            
            # Show cached indicator if this is from cache
            is_from_cache = cached_insights is not None and st.session_state.insights == cached_insights
            if is_from_cache:
                st.caption("📦 **Showing cached insights** · Click 'Generate AI Insights' to refresh")
            
            st.subheader("🤖 AI Qualitative Analysis")
            st.info(insights.get("executive_summary", "No summary available."))
            
            # Plotly Sentiment Gauge
            sentiment_score = insights.get("overall_sentiment_score", 0)
            gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = sentiment_score,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "AI Sentiment Score"},
                gauge = {
                    'axis': {'range': [0, 10]},
                    'bar': {'color': "#0F9D58" if sentiment_score >= 7 else ("#F4B400" if sentiment_score >= 4 else "#DB4437")}
                }
            ))
            gauge.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10))
            
            col_gauge, col_flaws, col_praises = st.columns([1.5, 2, 2])
            
            with col_gauge:
                st.plotly_chart(gauge, use_container_width=True)
                
            with col_flaws:
                st.markdown("#### 🚨 Top Flaws")
                for flaw in insights.get("top_flaws", []):
                    with st.expander(f"**{flaw.get('issue', 'Unknown')}**"):
                        st.write(f"*Evidence:* {flaw.get('frequency_mention', '')}")
                        
            with col_praises:
                st.markdown("#### 🌟 Top Praised Features")
                for feature in insights.get("top_praised_features", []):
                    with st.expander(f"**{feature.get('feature', 'Unknown')}**"):
                        st.write(f"*Reason:* {feature.get('reason', '')}")
            
            # Render Action Plan
            if st.session_state.action_plan:
                st.divider()
                st.subheader("💡 AI Prescriptive Strategy")
                
                # Add UI to regenerate or clear cache
                col_strategy_left, col_strategy_right = st.columns([4, 1])
                with col_strategy_right:
                    if st.button("🔄 Refresh", key="refresh_insights_btn"):
                        st.session_state.insights_cache.pop(selected_product, None)
                        reset_state()
                        st.rerun()
                
                st.markdown(st.session_state.action_plan)

else:
    st.info("👈 Please upload your multi-product dataset in the sidebar to begin.")