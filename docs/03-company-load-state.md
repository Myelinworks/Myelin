# Company Load State — PulseWear (Default Seed)

> Source: `__Product_launched.pdf`

This is the **seed state** loaded at Quarter 1 start. Every value here is a concrete initial
value for a DB column or `modifiers` row.

> ⚠️ **Conflict notice:** the worked-example reports (`12`–`16`) use a different company,
> "Nadi Wear," with materially different economics. See `README.md` § *Two conflicting company
> baselines* and `10-implementation-gaps.md`.

## Background

PulseWear is a 3-month-old Bengaluru-based startup developing AI-powered fitness smartwatches
for the Indian market. The company spent its first nine months on customer research, product
design, prototype development, OEM manufacturing partnerships, supply chain setup, hiring, and
go-to-market preparation. The first commercial smartwatch launched three months before Quarter 1
through the company's website, Amazon, and Flipkart. Early customer feedback has been
encouraging, validating the business idea, but the startup has not reached profitability. With a
functioning business, early traction, and six months of operating runway remaining, the company
enters Quarter 1 where every strategic decision directly impacts survival and growth.

## 1. Company profile

| Variable | Value |
|---|---|
| Company Name | PulseWear |
| Industry | Consumer Electronics |
| Category | Smart Wearables |
| Headquarters | Bengaluru, India |
| Company Age | 3 Months |
| Product Commercial Launch | 3 Months Ago |
| Company Stage | Seed Stage |
| Business Model | D2C Website + Amazon + Flipkart |
| Product | AI Smart Fitness Watch |
| Product Version | V1.0 |
| Target Customer | Urban Professionals (20–40 years) |
| Simulation Start | Quarter 1 |
| Simulation Duration | 4 Quarters |

## 2. Financial state

| Variable | Value |
|---|---|
| Total Capital Raised | ₹2.00 Cr |
| Company Valuation | ₹20.00 Cr (post-money) |
| Cash Available | ₹1.56 Cr |
| Available Credit Line | ₹50 L |
| Monthly Fixed Operating Cost | ₹26 L |
| Remaining Runway | 6 Months |

## 3. Product state

| Variable | Value |
|---|---|
| Product Status | Commercially Available |
| Selling Price | ₹10,000 |
| Manufacturing Cost | ₹4,500 |
| Gross Margin | 55% |
| Product Quality | 72 / 100 |
| Product Reliability | 94 / 100 |
| Feature Completeness | 78 / 100 |
| Average Product Rating | 4.3 / 5 |
| Warranty | 12 Months |
| Product Defect Rate | 2% |

## 4. Brand & digital state

| Variable | Value |
|---|---|
| Brand Awareness | 8 / 100 |
| Brand Trust | 55 / 100 |
| Brand Reputation | 58 / 100 |
| Brand Positioning | Affordable Premium Smartwatch Brand |
| Website | Live |
| Amazon Store | Active |
| Flipkart Store | Active |
| Organic Monthly Website Visitors | 8,000 |
| Email Subscribers | 3,600 |
| Social Media Followers | 11,500 |
| Community Members | 1,200 |
| Average Product Rating | 4.3 / 5 |

## 5. Customer state

| Variable | Value |
|---|---|
| Total Units Manufactured | 2,500 |
| Quality Rejected Units | 50 |
| Saleable Units Produced | 2,450 |
| Units Sold | 550 |
| Product Returns | 20 |
| Active Customers | 530 |
| Registered Customers | 920 |
| Customer Satisfaction | 78 / 100 |
| Customer Trust | 74 / 100 |
| Net Promoter Score | 32 |
| Referral Strength | 18 / 100 |

## 6. Sales state

| Variable | Value |
|---|---|
| Sales Channels | Website, Amazon, Flipkart |
| Sales Team Size | 5 |
| Sales Capability | 68 / 100 |
| CRM System | Operational |
| Order Fulfilment | Operational |

## 7. Operations state

| Variable | Value |
|---|---|
| Manufacturing Model | OEM / Contract Manufacturer |
| Manufacturing Partner | Contract Signed |
| Finished Goods Inventory | 1,920 Units |
| Production Capacity | 3,000 Units / Quarter |
| Warehouse Capacity | 5,000 Units |
| Supplier Reliability | 87 / 100 |
| Manufacturing Efficiency | 82 / 100 |
| Logistics Efficiency | 76 / 100 |
| Procurement Efficiency | 74 / 100 |

## 8. People state

| Variable | Value |
|---|---|
| Total Employees | 25 |
| Engineering Team | 8 |
| Marketing Team | 4 |
| Sales Team | 5 |
| Operations Team | 4 |
| Customer Success Team | 2 |
| HR & Administration | 2 |
| Employee Morale | 76 / 100 |
| Employee Productivity | 81 / 100 |

## 9. Market state

| Variable | Value |
|---|---|
| Target Market | India |
| Smartwatch Market Size | ₹4,500 Cr |
| Annual Market Growth | 18% |
| Competition Level | High |
| Primary Competitors | Noise, boAt, Fire-Boltt |
| Inflation | 5% |
| Technology Adoption | High |
| Economic Outlook | Stable |

## 10. Company status flags

| Variable | Value |
|---|---|
| Product Development | Complete |
| Manufacturing | Operational |
| Inventory Available | Yes |
| Website | Live |
| Amazon Marketplace | Live |
| Flipkart Marketplace | Live |
| Customer Support | Email + Live Chat |
| Marketing Operations | Active |
| Sales Operations | Active |
| Ready for Quarter 1 | Yes |

## 11. Hidden engine state

These are **not shown to the student**. They initialise the cognitive/momentum layer.

| Variable | Initial Value |
|---|---|
| Strategic Thinking | 50 |
| Leadership | 50 |
| Adaptability | 50 |
| Systems Thinking | 50 |
| Risk Appetite | 50 |
| Decision Consistency | 50 |
| Long-Term Thinking | 50 |
| Brand Momentum | 50 |
| Product Momentum | 50 |
| Investor Confidence | 60 |
| Employee Burnout | 10 |

## Consistency invariants (stated in source)

- Product launched 3 months ago (not 12 months ago)
- ₹20 Cr post-money valuation is **fixed**
- ₹2 Cr total capital raised is **fixed**
- ₹1.56 Cr cash aligns with a 6-month runway at ₹26 L/month burn
- Manufacturing, inventory, sales, returns, and active customers reconcile mathematically
  (2,500 manufactured − 50 rejected = 2,450 saleable; 550 sold − 20 returns = 530 active)
- Only approved sales channels (Website, Amazon, Flipkart) are included
- No funding events or new investment rounds are left open
