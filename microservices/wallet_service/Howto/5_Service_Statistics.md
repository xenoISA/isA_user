# How to Access Wallet Service Statistics

## Overview
The Wallet Service provides comprehensive statistics at both service-level and individual wallet/user levels.

## 1. Service-Wide Statistics

### Endpoint
```
GET /api/v1/wallet/stats
```

### Example Request
```bash
curl -X GET http://localhost:8209/api/v1/wallet/stats
```

### Response
```json
{
  "total_wallets": 150,
  "active_wallets": 120,
  "total_balance_all_wallets": 50000.0,
  "total_transactions_today": 450,
  "total_transactions_all_time": 15000,
  "average_wallet_balance": 333.33,
  "service_health": "healthy",
  "database_connected": true,
  "last_transaction_time": "2025-09-26T06:39:59.031868Z",
  "stats_generated_at": "2025-09-26T07:00:00.000000Z"
}
```

## 2. User-Level Statistics

### Endpoint
```
GET /api/v1/users/{user_id}/statistics
```

### Query Parameters
- `start_date`: Beginning of period (ISO format)
- `end_date`: End of period (ISO format)

### Example Request
```bash
curl -X GET "http://localhost:8209/api/v1/users/user-123/statistics?start_date=2025-09-01&end_date=2025-09-30"
```

### Response
```json
{
  "user_id": "user-123",
  "period": {
    "start": "2025-09-01T00:00:00Z",
    "end": "2025-09-30T23:59:59Z"
  },
  "wallet_count": 2,
  "total_balance": 250.0,
  "statistics": {
    "total_deposits": 500.0,
    "deposit_count": 5,
    "total_withdrawals": 100.0,
    "withdrawal_count": 2,
    "total_consumed": 150.0,
    "consumption_count": 30,
    "total_transferred_in": 50.0,
    "transfer_in_count": 3,
    "total_transferred_out": 25.0,
    "transfer_out_count": 1,
    "total_fees_paid": 5.0,
    "total_refunds_received": 10.0,
    "refund_count": 1
  },
  "daily_average": {
    "deposits": 16.67,
    "withdrawals": 3.33,
    "consumption": 5.0
  },
  "most_active_wallet": "wallet-id-1",
  "last_transaction": "2025-09-26T06:39:59.031868Z"
}
```

## 3. Wallet-Level Statistics

### Endpoint
```
GET /api/v1/wallets/{wallet_id}/statistics
```

### Query Parameters
- `start_date`: Beginning of period
- `end_date`: End of period
- `group_by`: day, week, or month

### Example Request
```bash
curl -X GET "http://localhost:8209/api/v1/wallets/{wallet_id}/statistics?group_by=day"
```

### Response
```json
{
  "wallet_id": "e1cd42e0-1f0e-427c-aae0-41252df580c0",
  "current_balance": 110.0,
  "period": {
    "start": "2025-09-01T00:00:00Z",
    "end": "2025-09-30T23:59:59Z"
  },
  "summary": {
    "total_inflow": 150.0,
    "total_outflow": 40.0,
    "net_change": 110.0,
    "transaction_count": 4,
    "average_transaction": 47.5
  },
  "by_type": {
    "deposits": {
      "count": 2,
      "total": 150.0,
      "average": 75.0
    },
    "withdrawals": {
      "count": 1,
      "total": 30.0,
      "average": 30.0
    },
    "consumption": {
      "count": 1,
      "total": 10.0,
      "average": 10.0
    }
  },
  "daily_breakdown": [
    {
      "date": "2025-09-26",
      "deposits": 150.0,
      "withdrawals": 30.0,
      "consumption": 10.0,
      "balance_end_of_day": 110.0
    }
  ]
}
```

## 4. Health Check

### Endpoint
```
GET /health
```

### Example Request
```bash
curl -X GET http://localhost:8209/health
```

### Response
```json
{
  "status": "healthy",
  "service": "wallet_service",
  "port": 8209,
  "version": "1.0.0"
}
```

## 5. Advanced Analytics Queries

### Top Users by Balance
```bash
curl -X GET "http://localhost:8209/api/v1/wallet/stats?metric=top_users&limit=10"
```

### Transaction Volume by Hour
```bash
curl -X GET "http://localhost:8209/api/v1/wallet/stats?metric=hourly_volume&date=2025-09-26"
```

### Service Growth Metrics
```bash
curl -X GET "http://localhost:8209/api/v1/wallet/stats?metric=growth&period=30d"
```

## Metrics Explained

### Service Metrics
- **total_wallets**: All wallets ever created
- **active_wallets**: Wallets with activity in last 30 days
- **total_balance_all_wallets**: Sum of all wallet balances
- **average_wallet_balance**: Mean balance across all wallets

### Transaction Metrics
- **total_transactions_today**: Count since 00:00 UTC
- **total_transactions_all_time**: Historical count
- **transaction_volume**: Sum of transaction amounts

### Health Metrics
- **service_health**: Overall service status
- **database_connected**: Database connectivity
- **last_transaction_time**: Most recent transaction timestamp

## Best Practices

1. **Cache Statistics**
   - Service stats can be cached for 1-5 minutes
   - User stats can be cached for longer periods
   - Real-time data should bypass cache

2. **Use Appropriate Granularity**
   - Daily for detailed analysis
   - Weekly for trends
   - Monthly for reports

3. **Filter by Date Range**
   - Avoid querying all-time data frequently
   - Use specific date ranges for better performance
   - Consider data retention policies

4. **Monitor Key Metrics**
   - Set alerts for unusual activity
   - Track growth trends
   - Monitor error rates

## Error Handling

### Statistics Not Available
```json
{
  "detail": "404: Statistics not available for this period"
}
```

### Invalid Date Range
```json
{
  "detail": "Invalid date range: start_date must be before end_date"
}
```

### Service Unavailable
```json
{
  "detail": "503: Statistics service temporarily unavailable"
}
```