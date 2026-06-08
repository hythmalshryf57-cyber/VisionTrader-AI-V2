import pytest
import asyncio
from backend.services.multi_tf_analyzer import full_multi_tf_analysis

@pytest.mark.asyncio
async def test_full_multi_tf_analysis():
    # Test fallback text generation (no API key)
    result = await full_multi_tf_analysis(
        symbol="XAUUSD",
        trade_type="يومي",
        user_id=None,
        api_key=None
    )
    
    assert "symbol" in result
    assert result["symbol"] == "XAUUSD"
    assert "timeframes_analyzed" in result
    assert isinstance(result["timeframes_analyzed"], list)
    
    # "يومي" should map to ["H4", "H1", "M15"]
    assert "H4" in result["timeframes_analyzed"]
    
    assert "final_analysis" in result
    assert "XAUUSD" in result["final_analysis"]
    
    # Check if the fallback text indicates success
    assert "الإشارة الإجمالية" in result["final_analysis"]
