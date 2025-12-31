import vertexai
from vertexai.generative_models import GenerativeModel
import os

def test_simple():
    project_id = "mobiusos-482817"
    location = "us-central1"
    
    print(f"👉 Init Vertex: {project_id}")
    vertexai.init(project=project_id, location=location)
    
    # Try the most generic model first
    model_id = "gemini-1.5-pro" 
    print(f"👉 Probing {model_id}...")
    
    try:
        model = GenerativeModel(model_id)
        resp = model.generate_content("hi")
        print("✅ SUCCESS!")
        print(resp.text)
    except Exception as e:
        print(f"❌ FAILED: {e}")

if __name__ == "__main__":
    test_simple()
