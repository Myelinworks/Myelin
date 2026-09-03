import asyncio
import asyncpg

async def test():
    try:
        conn = await asyncpg.connect(user='postgres', password='Idk@1355', host='db.ocoujlblpltubhsoluxv.supabase.co', port=5432, database='postgres')
        print('SUCCESS with Idk@1355 on db direct')
        await conn.close()
    except Exception as e:
        print('FAIL direct:', type(e).__name__)
        try:
            conn = await asyncpg.connect(user='postgres.ocoujlblpltubhsoluxv', password='Idk%401355', host='aws-0-ap-south-1.pooler.supabase.com', port=5432, database='postgres')
            print('SUCCESS with Idk%401355')
            await conn.close()
        except Exception as e2:
            print('FAIL both:', type(e2).__name__)

asyncio.run(test())
