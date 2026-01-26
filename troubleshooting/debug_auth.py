import os
import anthropic

def test_key():
    print("Checking ANTHROPIC_API_KEY...")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
        print("Run: export ANTHROPIC_API_KEY='your_key_here'")
        return

    print(f"Key found. Length: {len(api_key)}")
    print(f"Prefix: {api_key[:4]}...")
    
    # Check if it looks like a standard API Key (Starts with sk-)
    if not api_key.startswith("sk-"):
        print("\n" + "="*50)
        print("CRITICAL WARNING: The key does NOT start with 'sk-'.")
        print("Anthropic API keys typically start with 'sk-ant-'.")
        print("Please get a valid key from: https://console.anthropic.com/settings/keys")
        print("="*50 + "\n")

    print(f"Attempting to configure `anthropic` client with the provided key...")
    client = anthropic.Anthropic(api_key=api_key)
    
    try:
        print("Sending test prompt to Claude...")
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": "Hello"}
            ]
        )
        print("\nSUCCESS: API Key is valid and working!")
        print(f"Response: {message.content[0].text}")
    except Exception as e:
        print("\nFAILURE: API Call Failed.")
        print(f"Error: {e}")

if __name__ == "__main__":
    test_key()
