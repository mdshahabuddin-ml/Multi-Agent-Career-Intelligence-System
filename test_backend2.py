import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(base_url='http://localhost:8000', timeout=10.0, follow_redirects=True) as client:
        # Test root
        resp = await client.get('/')
        print(f'Root: {resp.status_code} - {resp.json()}')
        
        # Test openapi schema to see if jobs routes are in the schema
        resp = await client.get('/openapi.json')
        if resp.status_code == 200:
            schema = resp.json()
            paths = schema.get('paths', {})
            jobs_paths = [p for p in paths if p.startswith('/jobs')]
            print(f'Jobs paths in OpenAPI: {len(jobs_paths)}')
            for p in sorted(jobs_paths):
                print(f'  {p}')
        else:
            print(f'OpenAPI error: {resp.status_code}')
        
        # Test jobs search POST
        resp = await client.post('/jobs/search', json={'query': 'python', 'limit': 5})
        print(f'Jobs search POST: {resp.status_code}')
        if resp.status_code == 200:
            data = resp.json()
            jobs = data.get('jobs', [])
            print(f'  Jobs found: {len(jobs)}')
        else:
            print(f'  Error: {resp.text}')

asyncio.run(test())