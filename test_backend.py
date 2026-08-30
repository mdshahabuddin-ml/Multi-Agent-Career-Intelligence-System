import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(base_url='http://localhost:8000', timeout=10.0, follow_redirects=True) as client:
        # Test root
        resp = await client.get('/')
        print(f'Root: {resp.status_code} - {resp.json()}')
        
        # Test health
        resp = await client.get('/health')
        print(f'Health: {resp.status_code} - {resp.json()}')
        
        # Test docs
        resp = await client.get('/docs')
        print(f'Docs: {resp.status_code}')
        
        # Test jobs search POST
        resp = await client.post('/jobs/search', json={'query': 'python', 'limit': 5})
        print(f'Jobs search POST: {resp.status_code}')
        print(f'  Response: {resp.text}')
        
        # Test jobs search GET
        resp = await client.get('/jobs/search?query=python&limit=5')
        print(f'Jobs search GET: {resp.status_code}')
        print(f'  Response: {resp.text}')
        
        # Test jobs list
        resp = await client.get('/jobs')
        print(f'Jobs list: {resp.status_code}')
        print(f'  Response: {resp.text}')

asyncio.run(test())