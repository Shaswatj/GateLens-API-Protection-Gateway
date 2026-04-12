import asyncio
from core.decision import evaluate_request
from unittest.mock import AsyncMock, MagicMock

async def test():
    print("\n=== Testing evaluate_request function ===\n")
    
    # Create mock request
    request = AsyncMock()
    request.method = "GET"
    request.url = MagicMock()
    request.url.path = "/test"
    request.headers = {}
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.query_params = {"param": "hello"}
    
    try:
        result = await evaluate_request(request, b"", "127.0.0.1")
        print("✓ evaluate_request ran successfully\n")
        print(f"Result keys: {list(result.keys())}\n")
        
        # Check for new fields
        if 'ip_score' in result:
            print(f"✓ ip_score field present: {result['ip_score']}")
        else:
            print("✗ ip_score field MISSING")
        
        if 'threat_level' in result:
            print(f"✓ threat_level field present: {result['threat_level']}")
        else:
            print("✗ threat_level field MISSING")
        
        print(f"\nStatus: {result.get('status')}")
        print(f"Score: {result.get('score')}")
        print(f"Reasons: {result.get('reasons')}")
        
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
