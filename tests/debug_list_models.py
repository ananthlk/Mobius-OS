import google.cloud.aiplatform
from google.cloud import aiplatform

def list_vertex_models():
    project_id = "mobiusos-482817"
    location = "us-central1"
    
    print(f"📋 Listing Models for {project_id} in {location}...")
    
    try:
        aiplatform.init(project=project_id, location=location)
        
        # Use ModelGarden/PublisherDiscovery
        # Actually ModelServiceClient lists *custom* models usually.
        # To list *Publisher* (Gemini) models, we query the publisher location.
        
        from google.cloud import aiplatform_v1
        
        # Try ModelGardenServiceClient
        client = aiplatform_v1.ModelGardenServiceClient(
            client_options={"api_endpoint": f"{location}-aiplatform.googleapis.com"}
        )
        parent = f"projects/{project_id}/locations/{location}/publishers/google"
        
        print(f"   Querying: {parent}")
        # Request object might be needed or just pass parent
        # list_publisher_models(parent=...)
        response = client.list_publisher_models(parent=parent)
        
        found = []
        print("\n✅ Available Publisher Models:")
        for model in response:
            # Model name is full path: projects/.../publishers/google/models/gemini-pro
            short_name = model.name.split('/')[-1]
            if "gemini" in short_name.lower():
                print(f"   - {short_name}")
                found.append(short_name)
                
        if not found:
            print("   ⚠️ No Gemini models found in list.")
            
    except Exception as e:
        print(f"\n❌ List Failed: {e}")

if __name__ == "__main__":
    list_vertex_models()
