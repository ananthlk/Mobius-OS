try:
    import vertexai
    print(f"✅ vertexai found at {vertexai.__file__}")
except ImportError:
    print("❌ vertexai NOT found")

try:
    from vertexai.generative_models import GenerativeModel
    print("✅ GenerativeModel import SUCCESS")
except ImportError as e:
    print(f"❌ GenerativeModel import FAILED: {e}")
except Exception as e:
    print(f"❌ Unexpected Error: {e}")
