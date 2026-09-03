import asyncio
import asyncpg

async def test():
    try:
        conn = await asyncpg.connect(user='postgres.ocoujlblpltubhsoluxv', password='g5X.*v2$aB&dmLn', host='aws-0-ap-south-1.pooler.supabase.com', port=5432, database='postgres')
        print('SUCCESS with new password on pooler')
        await conn.close()
    except Exception as e:
        print('FAIL pooler:', type(e).__name__)
        try:
            conn = await asyncpg.connect(user='postgres', password='g5X.*v2$aB&dmLn', host='db.ocoujlblpltubhsoluxv.supabase.co', port=5432, database='postgres')
            print('SUCCESS with new password on direct')
            await conn.close()
        except Exception as e2:
            print('FAIL direct:', type(e2).__name__)

asyncio.run(test())
