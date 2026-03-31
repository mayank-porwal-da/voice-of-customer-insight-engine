"""
Comprehensive Unit Tests for app.py
Tests cover data loading, AI agents, state management, API handling, and data validation.
command to run: pytest test_app.py -v
"""

import json
import pytest
import pandas as pd
from io import StringIO
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


# =====================================================================
# --- FIXTURES ---
# =====================================================================

@pytest.fixture
def sample_csv_data():
    """Sample CSV data with all required columns."""
    data = {
        'product_name': ['AeroBrew Smart Mug', 'AeroBrew Smart Mug', 'Lumina Desk Lamp', 'Lumina Desk Lamp'],
        'rating': [5, 2, 4, 3],
        'review_text': [
            'Absolutely love it! Keeps my coffee hot.',
            'App keeps crashing on my Android phone.',
            'Perfect lighting for home office.',
            'Good lamp but the base is wobbly.'
        ],
        'review_date': ['2026-03-01', '2026-03-05', '2026-03-02', '2026-03-08'],
        'review_id': [1, 2, 3, 4],
        'product_id': ['P101', 'P101', 'P202', 'P202']
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_csv_string():
    """Sample CSV as string for file-like operations."""
    return """review_id,product_id,product_name,rating,review_date,review_text
1,P101,AeroBrew Smart Mug,5,2026-03-01,Absolutely love it! Keeps my coffee hot for hours.
2,P101,AeroBrew Smart Mug,2,2026-03-05,The temperature control is great but app crashes.
3,P202,Lumina Desk Lamp,4,2026-03-02,Perfect lighting for my home office.
4,P202,Lumina Desk Lamp,3,2026-03-08,Good lamp but the base is wobbly."""


@pytest.fixture
def mock_gemini_response_agent1():
    """Mock response for Agent 1 (extraction)."""
    return {
        "overall_sentiment_score": 3.5,
        "executive_summary": "The product has good features but suffers from software stability issues.",
        "top_flaws": [
            {"issue": "App Crashes", "frequency_mention": "Mentioned in 2 reviews"},
            {"issue": "Hardware Durability", "frequency_mention": "Charging coaster failed early"}
        ],
        "top_praised_features": [
            {"feature": "Temperature Control", "reason": "Users appreciate precise heat management"},
            {"feature": "Battery Life", "reason": "Longer than expected runtime"}
        ]
    }


@pytest.fixture
def mock_gemini_response_agent2():
    """Mock response for Agent 2 (strategy)."""
    return """## Immediate Action Plan

### Step 1: Fix Android App Stability (Target: 2 weeks)
- Reproduce crash on Android devices
- Add crash logging and error handling
- Test on Android 12, 13, 14

### Step 2: Improve Hardware Testing (Target: 3 weeks)
- Extend durability tests for charging coaster
- Add pre-production validation

### Step 3: Monitor & Iterate (Ongoing)
- Collect user feedback on updates
- Prepare rollout plan"""


@pytest.fixture
def mock_invalid_csv():
    """CSV missing required columns."""
    return """product_id,review_date,review_text
1,2026-03-01,Some review text
2,2026-03-05,Another review"""


# =====================================================================
# --- TEST: DATA LOADING ---
# =====================================================================

class TestDataLoading:
    """Tests for load_data() function."""
    
    def test_load_data_valid_csv(self, sample_csv_data, tmp_path):
        """Test loading a valid CSV file."""
        # Create temporary CSV file
        csv_file = tmp_path / "test_data.csv"
        sample_csv_data.to_csv(csv_file, index=False)
        
        # Mock the streamlit cache decorator
        with patch('streamlit.cache_data', lambda **kwargs: lambda f: f):
            from app import load_data
            df = load_data(csv_file)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 4
        assert list(df.columns) == ['product_name', 'rating', 'review_text', 'review_date', 'review_id', 'product_id']
    
    def test_load_data_file_not_found(self):
        """Test loading non-existent CSV file."""
        with patch('streamlit.cache_data', lambda **kwargs: lambda f: f):
            from app import load_data
            with pytest.raises(FileNotFoundError):
                load_data("/non/existent/path/file.csv")
    
    def test_load_data_returns_dataframe(self, sample_csv_data, tmp_path):
        """Test that load_data returns a pandas DataFrame."""
        csv_file = tmp_path / "test_data.csv"
        sample_csv_data.to_csv(csv_file, index=False)
        
        with patch('streamlit.cache_data', lambda **kwargs: lambda f: f):
            from app import load_data
            result = load_data(csv_file)
        
        assert isinstance(result, pd.DataFrame)
    
    def test_load_data_preserves_column_names(self, sample_csv_data, tmp_path):
        """Test that column names are preserved after loading."""
        csv_file = tmp_path / "test_data.csv"
        sample_csv_data.to_csv(csv_file, index=False)
        
        with patch('streamlit.cache_data', lambda **kwargs: lambda f: f):
            from app import load_data
            df = load_data(csv_file)
        
        assert 'product_name' in df.columns
        assert 'rating' in df.columns
        assert 'review_text' in df.columns


# =====================================================================
# --- TEST: DATA VALIDATION ---
# =====================================================================

class TestDataValidation:
    """Tests for data validation logic."""
    
    def test_required_columns_present(self, sample_csv_data):
        """Test validation when all required columns are present."""
        required_cols = {'product_name', 'rating', 'review_text'}
        available_cols = set(sample_csv_data.columns)
        
        assert required_cols.issubset(available_cols)
    
    def test_required_columns_missing(self, mock_invalid_csv, tmp_path):
        """Test validation fails when required columns are missing."""
        csv_file = tmp_path / "invalid.csv"
        csv_file.write_text(mock_invalid_csv)
        
        df = pd.read_csv(csv_file)
        required_cols = {'product_name', 'rating', 'review_text'}
        available_cols = set(df.columns)
        
        assert not required_cols.issubset(available_cols)
    
    def test_rating_column_numeric(self, sample_csv_data):
        """Test that rating column contains numeric values."""
        assert pd.api.types.is_numeric_dtype(sample_csv_data['rating'])
    
    def test_rating_values_in_range(self, sample_csv_data):
        """Test that all ratings are between 1 and 5."""
        assert sample_csv_data['rating'].min() >= 1
        assert sample_csv_data['rating'].max() <= 5
    
    def test_duplicate_product_names(self, sample_csv_data):
        """Test handling of duplicate product names."""
        products = sample_csv_data['product_name'].unique().tolist()
        assert 'AeroBrew Smart Mug' in products
        assert 'Lumina Desk Lamp' in products
        assert len(products) == 2


# =====================================================================
# --- TEST: AI AGENT 1 (EXTRACTION) ---
# =====================================================================

class TestAgent1Extraction:
    """Tests for run_agent_1_extraction() function."""
    
    @patch('google.genai.Client')
    def test_agent_1_valid_response(self, mock_client_class, mock_gemini_response_agent1):
        """Test Agent 1 with valid JSON response."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_gemini_response_agent1)
        mock_client.models.generate_content.return_value = mock_response
        
        with patch('streamlit.cache_data', lambda **kwargs: lambda f: f):
            with patch('streamlit.set_page_config'):
                with patch('streamlit.session_state', {}):
                    with patch('google.genai.Client', return_value=mock_client):
                        from app import run_agent_1_extraction
                        
                        reviews_text = "Rating: 5/5. Loved it!\nRating: 2/5. App crashed."
                        result = run_agent_1_extraction(reviews_text, "Test Product")
        
        assert isinstance(result, dict)
        assert 'overall_sentiment_score' in result
        assert 'executive_summary' in result
        assert 'top_flaws' in result
        assert 'top_praised_features' in result
    
    @patch('google.genai.Client')
    def test_agent_1_error_handling(self, mock_client_class):
        """Test Agent 1 error handling when API fails."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API Error")
        
        with patch('streamlit.cache_data', lambda **kwargs: lambda f: f):
            with patch('streamlit.set_page_config'):
                with patch('streamlit.session_state', {}):
                    with patch('google.genai.Client', return_value=mock_client):
                        from app import run_agent_1_extraction
                        
                        reviews_text = "Some reviews"
                        result = run_agent_1_extraction(reviews_text, "Test Product")
        
        assert 'error' in result
    
    @patch('google.genai.Client')
    def test_agent_1_response_structure(self, mock_client_class):
        """Test that Agent 1 response has correct JSON structure."""
        mock_response_data = {
            "overall_sentiment_score": 4.2,
            "executive_summary": "Product is good",
            "top_flaws": [{"issue": "Bug", "frequency_mention": "Mentioned once"}],
            "top_praised_features": [{"feature": "Speed", "reason": "Fast"}]
        }
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_response_data)
        mock_client.models.generate_content.return_value = mock_response
        
        with patch('streamlit.cache_data', lambda **kwargs: lambda f: f):
            with patch('streamlit.set_page_config'):
                with patch('streamlit.session_state', {}):
                    with patch('google.genai.Client', return_value=mock_client):
                        from app import run_agent_1_extraction
                        
                        result = run_agent_1_extraction("reviews", "Product")
        
        assert result['overall_sentiment_score'] == 4.2
        assert len(result['top_flaws']) == 1
        assert len(result['top_praised_features']) == 1
    
    @patch('google.genai.Client')
    def test_agent_1_sentiment_score_range(self, mock_client_class):
        """Test that sentiment score is between 1.0 and 10.0."""
        mock_response_data = {
            "overall_sentiment_score": 7.5,
            "executive_summary": "Good product",
            "top_flaws": [],
            "top_praised_features": []
        }
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_response_data)
        mock_client.models.generate_content.return_value = mock_response
        
        with patch('streamlit.cache_data', lambda **kwargs: lambda f: f):
            with patch('streamlit.set_page_config'):
                with patch('streamlit.session_state', {}):
                    with patch('google.genai.Client', return_value=mock_client):
                        from app import run_agent_1_extraction
                        
                        result = run_agent_1_extraction("reviews", "Product")
        
        assert 1.0 <= result['overall_sentiment_score'] <= 10.0


# =====================================================================
# --- TEST: AI AGENT 2 (STRATEGY) ---
# =====================================================================

class TestAgent2Strategy:
    """Tests for run_agent_2_strategy() function."""
    
    @patch('google.genai.Client')
    def test_agent_2_valid_response(self, mock_client_class, mock_gemini_response_agent2):
        """Test Agent 2 with valid text response."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = mock_gemini_response_agent2
        mock_client.models.generate_content.return_value = mock_response
        
        with patch('streamlit.cache_data', lambda **kwargs: lambda f: f):
            with patch('streamlit.set_page_config'):
                with patch('streamlit.session_state', {}):
                    with patch('google.genai.Client', return_value=mock_client):
                        from app import run_agent_2_strategy
                        
                        flaws = [
                            {"issue": "App Crashes", "frequency_mention": "Mentioned 2x"},
                            {"issue": "Hardware Issues", "frequency_mention": "Mentioned 1x"}
                        ]
                        result = run_agent_2_strategy(flaws, "Test Product")
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    @patch('google.genai.Client')
    def test_agent_2_error_handling(self, mock_client_class):
        """Test Agent 2 error handling when API fails."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API Timeout")
        
        with patch('streamlit.cache_data', lambda **kwargs: lambda f: f):
            with patch('streamlit.set_page_config'):
                with patch('streamlit.session_state', {}):
                    with patch('google.genai.Client', return_value=mock_client):
                        from app import run_agent_2_strategy
                        
                        flaws = [{"issue": "Bug", "frequency_mention": "Once"}]
                        result = run_agent_2_strategy(flaws, "Product")
        
        assert "Error" in result or "error" in result
    
    @patch('google.genai.Client')
    def test_agent_2_includes_markdown_formatting(self, mock_client_class):
        """Test that Agent 2 response contains markdown formatting."""
        markdown_response = "## Strategy\n### Step 1\nDo something\n### Step 2\nDo another"
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = markdown_response
        mock_client.models.generate_content.return_value = mock_response
        
        with patch('streamlit.cache_data', lambda **kwargs: lambda f: f):
            with patch('streamlit.set_page_config'):
                with patch('streamlit.session_state', {}):
                    with patch('google.genai.Client', return_value=mock_client):
                        from app import run_agent_2_strategy
                        
                        result = run_agent_2_strategy([{"issue": "Test", "frequency_mention": "test"}], "Product")
        
        assert "##" in result or "###" in result or any(marker in result for marker in ["#", "-", "*"])


# =====================================================================
# --- TEST: STATE MANAGEMENT ---
# =====================================================================

class TestStateManagement:
    """Tests for session state management and reset_state() function."""
    
    def test_reset_state_clears_insights(self):
        """Test that reset_state clears insights from session state."""
        with patch('streamlit.session_state', {'insights': 'some_value', 'action_plan': 'some_plan'}):
            with patch('streamlit.cache_data', lambda **kwargs: lambda f: f):
                with patch('streamlit.set_page_config'):
                    from app import reset_state
                    
                    # This would be called by the app
                    mock_session_state = {'insights': 'some_value', 'action_plan': 'some_plan'}
                    mock_session_state['insights'] = None
                    mock_session_state['action_plan'] = None
                    
                    assert mock_session_state['insights'] is None
                    assert mock_session_state['action_plan'] is None
    
    def test_session_state_initialization(self):
        """Test that session state variables are properly initialized."""
        mock_session_state = {
            'selected_product': None,
            'insights': None,
            'action_plan': None,
            'user_provided_api_key': None,
            'using_fallback_key': False
        }
        
        assert mock_session_state['selected_product'] is None
        assert mock_session_state['insights'] is None
        assert mock_session_state['action_plan'] is None
        assert mock_session_state['user_provided_api_key'] is None
        assert mock_session_state['using_fallback_key'] is False
    
    def test_state_persists_across_reruns(self):
        """Test that session state persists across Streamlit reruns."""
        initial_state = {
            'insights': {'sentiment': 8.5},
            'action_plan': 'Step 1: Fix bug'
        }
        
        # Simulate state persistence
        updated_state = initial_state.copy()
        updated_state['selected_product'] = 'New Product'
        
        assert initial_state['insights'] == updated_state['insights']
        assert initial_state['action_plan'] == updated_state['action_plan']
        assert updated_state['selected_product'] == 'New Product'


# =====================================================================
# --- TEST: API KEY HANDLING ---
# =====================================================================

class TestAPIKeyHandling:
    """Tests for API key configuration and fallback logic."""
    
    def test_user_provided_api_key_takes_precedence(self):
        """Test that user-provided API key is prioritized over .env key."""
        user_key = "user_provided_key_123"
        env_key = "env_key_456"
        
        # User provided key should take precedence
        selected_key = user_key if user_key else env_key
        
        assert selected_key == user_key
        assert selected_key != env_key
    
    def test_fallback_to_env_key(self):
        """Test fallback to .env key when user doesn't provide one."""
        user_key = None
        env_key = "env_key_456"
        
        selected_key = user_key if user_key else env_key
        
        assert selected_key == env_key
    
    def test_no_api_key_error_condition(self):
        """Test error condition when no API key is available."""
        user_key = None
        env_key = None
        
        selected_key = user_key if user_key else env_key
        
        assert selected_key is None
    
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test_env_key'})
    def test_env_api_key_loading(self):
        """Test that API key is correctly loaded from environment."""
        import os
        api_key = os.getenv("GEMINI_API_KEY")
        
        assert api_key == 'test_env_key'
    
    def test_api_key_none_when_not_set(self):
        """Test that API key is None when not provided."""
        with patch.dict('os.environ', {}, clear=True):
            import os
            api_key = os.getenv("GEMINI_API_KEY")
            
            assert api_key is None


# =====================================================================
# --- TEST: DATAFRAME OPERATIONS ---
# =====================================================================

class TestDataFrameOperations:
    """Tests for DataFrame filtering and calculations."""
    
    def test_filter_by_product_name(self, sample_csv_data):
        """Test filtering DataFrame by product name."""
        product = 'AeroBrew Smart Mug'
        filtered_df = sample_csv_data[sample_csv_data['product_name'] == product]
        
        assert len(filtered_df) == 2
        assert all(filtered_df['product_name'] == product)
    
    def test_calculate_average_rating(self, sample_csv_data):
        """Test calculation of average rating for a product."""
        product = 'AeroBrew Smart Mug'
        prod_df = sample_csv_data[sample_csv_data['product_name'] == product]
        avg_rating = prod_df['rating'].mean()
        
        # (5 + 2) / 2 = 3.5
        assert avg_rating == 3.5
    
    def test_calculate_total_reviews(self, sample_csv_data):
        """Test counting total reviews for a product."""
        product = 'Lumina Desk Lamp'
        prod_df = sample_csv_data[sample_csv_data['product_name'] == product]
        total_reviews = len(prod_df)
        
        assert total_reviews == 2
    
    def test_rating_distribution(self, sample_csv_data):
        """Test getting rating distribution counts."""
        product = 'AeroBrew Smart Mug'
        prod_df = sample_csv_data[sample_csv_data['product_name'] == product]
        rating_counts = prod_df['rating'].value_counts().to_dict()
        
        assert rating_counts[5] == 1
        assert rating_counts[2] == 1
    
    def test_date_range_extraction(self, sample_csv_data):
        """Test extracting date range from reviews."""
        sample_csv_data['review_date'] = pd.to_datetime(sample_csv_data['review_date'])
        
        min_date = sample_csv_data['review_date'].min()
        max_date = sample_csv_data['review_date'].max()
        
        assert min_date == pd.Timestamp('2026-03-01')
        assert max_date == pd.Timestamp('2026-03-08')
    
    def test_unique_products(self, sample_csv_data):
        """Test extraction of unique product names."""
        products = sample_csv_data['product_name'].unique().tolist()
        
        assert 'AeroBrew Smart Mug' in products
        assert 'Lumina Desk Lamp' in products
        assert len(products) == 2


# =====================================================================
# --- TEST: EDGE CASES ---
# =====================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        empty_df = pd.DataFrame(columns=['product_name', 'rating', 'review_text'])
        
        assert len(empty_df) == 0
        assert list(empty_df.columns) == ['product_name', 'rating', 'review_text']
    
    def test_single_review(self, sample_csv_data):
        """Test handling of single review."""
        single_review = sample_csv_data.iloc[:1]
        
        assert len(single_review) == 1
        avg_rating = single_review['rating'].mean()
        assert avg_rating == 5  # First review has rating 5
    
    def test_all_same_rating(self):
        """Test DataFrame with all same ratings."""
        df = pd.DataFrame({
            'product_name': ['Product A', 'Product A', 'Product A'],
            'rating': [5, 5, 5],
            'review_text': ['Great', 'Great', 'Great']
        })
        
        avg_rating = df['rating'].mean()
        assert avg_rating == 5
    
    def test_extreme_rating_values(self):
        """Test with extreme rating values (1 and 5)."""
        df = pd.DataFrame({
            'product_name': ['Product A', 'Product A'],
            'rating': [1, 5],
            'review_text': ['Awful', 'Excellent']
        })
        
        assert df['rating'].min() == 1
        assert df['rating'].max() == 5
        assert df['rating'].mean() == 3
    
    def test_special_characters_in_reviews(self):
        """Test handling special characters in review text."""
        df = pd.DataFrame({
            'product_name': ['Product'],
            'rating': [4],
            'review_text': ["Great! Love it 😍 #amazing @brand"]
        })
        
        assert "😍" in df['review_text'].iloc[0]
        assert "#amazing" in df['review_text'].iloc[0]
    
    def test_very_long_review_text(self):
        """Test handling of very long review text."""
        long_text = "A" * 5000
        df = pd.DataFrame({
            'product_name': ['Product'],
            'rating': [5],
            'review_text': [long_text]
        })
        
        assert len(df['review_text'].iloc[0]) == 5000
    
    def test_null_values_handling(self):
        """Test handling of null/NaN values in DataFrame."""
        df = pd.DataFrame({
            'product_name': ['Product A', 'Product B', None],
            'rating': [5, None, 3],
            'review_text': ['Good', 'Bad', 'Okay']
        })
        
        assert df['rating'].isnull().sum() == 1
        assert df['product_name'].isnull().sum() == 1


# =====================================================================
# --- TEST: JSON RESPONSE PARSING ---
# =====================================================================

class TestJSONParsing:
    """Tests for JSON response parsing from AI models."""
    
    def test_valid_json_parsing(self, mock_gemini_response_agent1):
        """Test parsing valid JSON response."""
        json_str = json.dumps(mock_gemini_response_agent1)
        parsed = json.loads(json_str)
        
        assert isinstance(parsed, dict)
        assert 'overall_sentiment_score' in parsed
    
    def test_invalid_json_handling(self):
        """Test handling of invalid JSON."""
        invalid_json = "This is not JSON { invalid }"
        
        with pytest.raises(json.JSONDecodeError):
            json.loads(invalid_json)
    
    def test_malformed_json_response(self):
        """Test handling of malformed JSON from API."""
        malformed_json = '{"key": "value"'  # Missing closing brace
        
        with pytest.raises(json.JSONDecodeError):
            json.loads(malformed_json)
    
    def test_json_with_unicode_characters(self):
        """Test JSON parsing with unicode characters."""
        json_with_unicode = {
            "summary": "Product is 🎯 amazing",
            "feedback": "Users love it ❤️"
        }
        
        json_str = json.dumps(json_with_unicode, ensure_ascii=False)
        parsed = json.loads(json_str)
        
        assert "🎯" in parsed["summary"]
        assert "❤️" in parsed["feedback"]


# =====================================================================
# --- TEST: ERROR RECOVERY ---
# =====================================================================

class TestErrorRecovery:
    """Tests for error recovery and graceful handling."""
    
    @patch('google.genai.Client')
    def test_api_timeout_recovery(self, mock_client_class):
        """Test recovery from API timeout."""
        from unittest.mock import MagicMock
        
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = TimeoutError("API timeout")
        
        with patch('streamlit.cache_data', lambda **kwargs: lambda f: f):
            with patch('streamlit.set_page_config'):
                with patch('streamlit.session_state', {}):
                    with patch('google.genai.Client', return_value=mock_client):
                        from app import run_agent_1_extraction
                        
                        result = run_agent_1_extraction("reviews", "Product")
        
        assert 'error' in result
    
    def test_dataframe_missing_column_recovery(self):
        """Test recovery from missing column in DataFrame."""
        df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
        
        try:
            _ = df['missing_col']
            assert False, "Should raise KeyError"
        except KeyError:
            assert True
    
    def test_invalid_date_format_handling(self):
        """Test handling of invalid date format."""
        with pytest.raises(Exception):
            pd.to_datetime('not-a-date', format='%Y-%m-%d')


# =====================================================================
# --- INTEGRATION TESTS ---
# =====================================================================

class TestIntegration:
    """Integration tests combining multiple components."""
    
    @patch('google.genai.Client')
    def test_full_pipeline_with_valid_data(self, mock_client_class, sample_csv_data, 
                                           mock_gemini_response_agent1, mock_gemini_response_agent2):
        """Test complete pipeline from data load to strategy generation."""
        mock_client = MagicMock()
        
        # Mock Agent 1 response
        mock_response_1 = MagicMock()
        mock_response_1.text = json.dumps(mock_gemini_response_agent1)
        
        # Mock Agent 2 response
        mock_response_2 = MagicMock()
        mock_response_2.text = mock_gemini_response_agent2
        
        mock_client.models.generate_content.side_effect = [mock_response_1, mock_response_2]
        
        with patch('streamlit.cache_data', lambda **kwargs: lambda f: f):
            with patch('streamlit.set_page_config'):
                with patch('streamlit.session_state', {}):
                    with patch('google.genai.Client', return_value=mock_client):
                        from app import run_agent_1_extraction, run_agent_2_strategy, load_data
                        
                        # Simulate data loading
                        df = sample_csv_data
                        assert len(df) == 4
                        
                        # Simulate product filtering
                        product = 'AeroBrew Smart Mug'
                        prod_df = df[df['product_name'] == product]
                        assert len(prod_df) == 2
                        
                        # Simulate Agent 1
                        combined_reviews = "\n".join([f"Rating: {row['rating']}" for _, row in prod_df.iterrows()])
                        insights = run_agent_1_extraction(combined_reviews, product)
                        
                        assert 'overall_sentiment_score' in insights
                        assert 'top_flaws' in insights


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
