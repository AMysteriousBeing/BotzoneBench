import argparse
import sys
from gemini_utils import query_gemini

# Default key from WORKFLOW_GUIDE.md
DEFAULT_API_KEY = ""

def main():
    parser = argparse.ArgumentParser(description="Test Gemini API interface.")
    parser.add_argument("--model", type=str, default="3 pro",
                        help="Model version or alias (e.g., '2.5 pro', 'gemini-3-pro-preview', 'flash')")
    parser.add_argument("--prompt", type=str, default="Tell me a short joke about programming.",
                        help="Prompt to send to the model")
    parser.add_argument("--key", type=str, default=DEFAULT_API_KEY,
                        help="Gemini API Key")

    args = parser.parse_args()

    print(f"--- Testing Gemini API Interface ---")
    print(f"Model: {args.model}")
    print(f"Prompt: {args.prompt}")
    print(f"------------------------------------")

    response = query_gemini(args.prompt, args.key, args.model)
    
    print("\nResponse:")
    print(response)

if __name__ == "__main__":
    main()

