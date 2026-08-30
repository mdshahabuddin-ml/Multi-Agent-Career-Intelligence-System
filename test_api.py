import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(base_url='http://localhost:8000', timeout=10.0, follow_redirects=True) as client:
        # Test jobs search POST
        resp = await client.post('/jobs/search', json={'query': 'python', 'limit': 5})
        print(f'Jobs search POST: {resp.status_code}')
        if resp.status_code == 200:
            data = resp.json()
            jobs = data.get('jobs', [])
            print(f'  Jobs found: {len(jobs)}')
            for job in jobs[:2]:
                print(f'  - {job.get("title")} at {job.get("company")}')
        else:
            print(f'  Error: {resp.text}')
        
        # Test jobs list GET
        resp = await client.get('/jobs/?query=python&limit=5')
        print(f'Jobs list GET: {resp.status_code}')
        if resp.status_code == 200:
            data = resp.json()
            jobs = data.get('jobs', [])
            print(f'  Jobs found: {len(jobs)}')
        else:
            print(f'  Error: {resp.text}')

asyncio.run(test())