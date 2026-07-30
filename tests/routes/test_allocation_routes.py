async def test_submitting_each_department_upserts_one_row(client, company_and_quarter):
    company, quarter = company_and_quarter
    base = f"/companies/{company.id}/quarters/{quarter.id}/allocations"

    marketing = await client.post(f"{base}/marketing", json={"google_ads": "4.00", "meta_ads": "1.92"})
    assert marketing.status_code == 200
    body = marketing.json()
    assert body["google_ads"] == "4.0000"
    assert body["reps"] == "0.0000"  # other departments' fields default to zero on first insert

    sales = await client.post(f"{base}/sales", json={"reps": "5.45", "crm_tools": "1.30"})
    assert sales.status_code == 200
    body = sales.json()
    # marketing's earlier submission survives the sales upsert -- one row, not one per department
    assert body["google_ads"] == "4.0000"
    assert body["reps"] == "5.4500"

    rnd = await client.post(f"{base}/rnd", json={"quality_qa": "2.75", "innovation": "2.25", "warranty_years": 1})
    assert rnd.status_code == 200
    assert rnd.json()["warranty_years"] == 1


async def test_resubmitting_the_same_department_overwrites_not_duplicates(client, company_and_quarter):
    company, quarter = company_and_quarter
    base = f"/companies/{company.id}/quarters/{quarter.id}/allocations"

    await client.post(f"{base}/hr", json={"culture_benefits": "1.00"})
    second = await client.post(f"{base}/hr", json={"culture_benefits": "2.00"})

    assert second.status_code == 200
    assert second.json()["culture_benefits"] == "2.0000"


async def test_allocations_are_rejected_once_the_quarter_is_locked(client, company_and_quarter):
    company, quarter = company_and_quarter
    base = f"/companies/{company.id}/quarters/{quarter.id}"

    await client.post(f"{base}/lock")
    response = await client.post(f"{base}/allocations/marketing", json={"google_ads": "4.00"})

    assert response.status_code == 409
