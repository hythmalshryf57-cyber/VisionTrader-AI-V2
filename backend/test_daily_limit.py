from services.trade_protection import trade_protection_service

# Test for user id 1 (admin created at startup)
res = trade_protection_service.refresh_protection(1)
print(res)
