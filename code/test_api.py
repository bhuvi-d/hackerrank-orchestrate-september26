import os, sys
sys.path.insert(0, 'code')

# Load .env
env_path = '.env'
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

key = os.environ.get('GOOGLE_API_KEY', '')
print(f'Key loaded: {key[:8]}...{key[-4:] if len(key) > 8 else ""}')

try:
    import google.generativeai as genai
    genai.configure(api_key=key)
    # Quick ping with minimal tokens
    model = genai.GenerativeModel('gemini-2.0-flash')
    resp = model.generate_content('Reply with only: OK')
    print(f'API test result: {resp.text.strip()}')
    print('SUCCESS: Gemini API is working')
except Exception as e:
    print(f'FAILED: {e}')
