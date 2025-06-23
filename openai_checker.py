#!/usr/bin/env python3
"""
Simple OpenAI API Checker
Works with project-scoped API keys and current OpenAI API limitations.
"""

import os
import requests
import json
from datetime import datetime
import argparse

class SimpleOpenAIChecker:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        self.base_url = 'https://api.openai.com/v1'
    
    def test_api_and_get_info(self):
        """Test API functionality and extract useful information."""
        print("🔍 SIMPLE OPENAI API CHECKER")
        print("=" * 50)
        
        # Test 1: Check if API key works
        print("🔑 Testing API key...")
        if not self.test_models_endpoint():
            return
        
        # Test 2: Make a completion request to get rate limits and usage info
        print("\n🧪 Testing chat completion...")
        self.test_completion_with_limits()
        
        # Test 3: Check available models
        print("\n🤖 Checking available models...")
        self.list_available_models()
        
        # Test 4: Show key information
        self.show_key_info()
        
        print("\n✅ All tests completed!")
    
    def test_models_endpoint(self) -> bool:
        """Test the models endpoint to verify API key."""
        try:
            response = requests.get(
                f'{self.base_url}/models',
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ API key is valid!")
                return True
            else:
                print(f"❌ API key test failed: {response.status_code}")
                if response.status_code == 401:
                    print("   This usually means the API key is invalid or expired.")
                elif response.status_code == 429:
                    print("   Rate limit exceeded. Try again later.")
                return False
                
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def test_completion_with_limits(self):
        """Test completion and extract rate limit information."""
        try:
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=self.headers,
                json={
                    'model': 'gpt-3.5-turbo',
                    'messages': [
                        {'role': 'user', 'content': 'Respond with exactly: "Test successful"'}
                    ],
                    'max_tokens': 10,
                    'temperature': 0
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract response info
                message = result['choices'][0]['message']['content'].strip()
                usage = result.get('usage', {})
                model_used = result.get('model', 'Unknown')
                
                print("✅ Chat completion successful!")
                print(f"🤖 Model: {model_used}")
                print(f"💬 Response: {message}")
                
                # Show token usage
                if usage:
                    print(f"\n📊 TOKEN USAGE:")
                    print(f"   Prompt tokens: {usage.get('prompt_tokens', 0)}")
                    print(f"   Completion tokens: {usage.get('completion_tokens', 0)}")
                    print(f"   Total tokens: {usage.get('total_tokens', 0)}")
                
                # Extract rate limit info from headers
                rate_info = self.extract_rate_limits(response)
                if rate_info:
                    print(f"\n⚡ RATE LIMITS:")
                    for key, value in rate_info.items():
                        print(f"   {key}: {value}")
                
                # Calculate rough cost estimate
                self.estimate_cost(usage, model_used)
                
            elif response.status_code == 429:
                print("⚠️  Rate limit exceeded!")
                rate_info = self.extract_rate_limits(response)
                if rate_info:
                    print("Current limits:")
                    for key, value in rate_info.items():
                        print(f"   {key}: {value}")
            else:
                print(f"❌ Completion failed: {response.status_code}")
                print(f"   Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Completion test error: {e}")
    
    def extract_rate_limits(self, response) -> dict:
        """Extract rate limit information from response headers."""
        rate_limits = {}
        
        # Common rate limit headers
        headers_map = {
            'x-ratelimit-limit-requests': 'Requests per minute limit',
            'x-ratelimit-limit-tokens': 'Tokens per minute limit',
            'x-ratelimit-remaining-requests': 'Requests remaining',
            'x-ratelimit-remaining-tokens': 'Tokens remaining',
            'x-ratelimit-reset-requests': 'Requests reset time',
            'x-ratelimit-reset-tokens': 'Tokens reset time'
        }
        
        for header, description in headers_map.items():
            value = response.headers.get(header)
            if value:
                rate_limits[description] = value
        
        return rate_limits
    
    def estimate_cost(self, usage: dict, model: str):
        """Estimate the cost of the API call."""
        if not usage:
            return
        
        # Rough cost estimates (as of 2024 - check OpenAI pricing for current rates)
        pricing = {
            'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},  # per 1K tokens
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
        }
        
        model_base = model.split('-')[0] + '-' + model.split('-')[1] if '-' in model else model
        
        if any(key in model.lower() for key in pricing.keys()):
            for key in pricing.keys():
                if key in model.lower():
                    rates = pricing[key]
                    break
            else:
                rates = pricing['gpt-3.5-turbo']  # Default
            
            prompt_cost = (usage.get('prompt_tokens', 0) / 1000) * rates['input']
            completion_cost = (usage.get('completion_tokens', 0) / 1000) * rates['output']
            total_cost = prompt_cost + completion_cost
            
            print(f"\n💰 ESTIMATED COST:")
            print(f"   This request: ~${total_cost:.6f}")
            print(f"   (Based on {model} pricing)")
    
    def list_available_models(self):
        """List available models."""
        try:
            response = requests.get(
                f'{self.base_url}/models',
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                models_data = response.json()
                models = models_data.get('data', [])
                
                if models:
                    print(f"📋 Available models: {len(models)} total")
                    
                    # Group models by type
                    gpt_models = [m for m in models if 'gpt' in m['id'].lower()]
                    dall_e_models = [m for m in models if 'dall-e' in m['id'].lower()]
                    embedding_models = [m for m in models if 'embedding' in m['id'].lower()]
                    tts_models = [m for m in models if 'tts' in m['id'].lower()]
                    
                    if gpt_models:
                        print(f"   🧠 GPT models: {len(gpt_models)}")
                        popular_gpt = [m['id'] for m in gpt_models if any(x in m['id'] for x in ['gpt-3.5-turbo', 'gpt-4'])]
                        for model in popular_gpt[:5]:
                            print(f"      • {model}")
                    
                    if dall_e_models:
                        print(f"   🎨 DALL-E models: {len(dall_e_models)}")
                        for model in dall_e_models:
                            print(f"      • {model['id']}")
                    
                    if embedding_models:
                        print(f"   🔗 Embedding models: {len(embedding_models)}")
                        for model in embedding_models[:3]:
                            print(f"      • {model['id']}")
                    
                    if tts_models:
                        print(f"   🔊 Text-to-Speech: {len(tts_models)}")
                else:
                    print("❌ No models found")
            else:
                print(f"❌ Failed to get models: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error getting models: {e}")
    
    def show_key_info(self):
        """Show information about the API key."""
        print(f"\n🔑 API KEY INFORMATION")
        print("=" * 50)
        
        # Analyze the key format
        key_parts = self.api_key.split('-')
        if len(key_parts) >= 2:
            key_type = key_parts[1]
            if key_type == 'proj':
                print("🏷️  Type: Project API Key")
                print("📋 Scope: Limited to specific project")
                print("🔒 Access: Chat completions, models, some endpoints")
            elif key_type == 'org':
                print("🏷️  Type: Organization API Key") 
                print("📋 Scope: Full organization access")
                print("🔒 Access: All endpoints including billing")
            else:
                print(f"🏷️  Type: {key_type} API Key")
        
        print(f"📅 Tested: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"✅ Status: Active and functional")
        
        print(f"\n💡 TIPS:")
        print("   • Project keys have limited billing access")
        print("   • Check OpenAI dashboard for detailed usage")
        print("   • Monitor your usage to avoid unexpected charges")
        print("   • Set up usage alerts in your OpenAI account")


def main():
    parser = argparse.ArgumentParser(description='Simple OpenAI API key checker')
    parser.add_argument('--api-key', '-k', help='OpenAI API key (or set OPENAI_API_KEY env var)')
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ No API key provided!")
        print("Use: python simple_checker.py --api-key sk-...")
        print("Or set: OPENAI_API_KEY environment variable")
        return
    
    # Run the checker
    checker = SimpleOpenAIChecker(api_key)
    checker.test_api_and_get_info()


if __name__ == '__main__':
    main()