import requests
from shared.auth import api  # Import the standard API session from the shared auth module

def placeOrder(instrument, buy_or_sell, qty, order_type, price, amo="regular"):
    """
    Wraps Shoonya API order placement with paper trading support.
    Expected usage: placeOrder("NIFTY24DEC75P24000", "SELL", 75, "MARKET", 0)
    """
    import os
    PAPER_TRADING = int(os.getenv("PAPER_TRADING", 1))
    
    if PAPER_TRADING == 1:
        print(f"[PAPER_ORDER] {buy_or_sell} {qty} {instrument} @ {order_type} {price}")
        return 0 # Simulated successful Order ID
    
    side = "B" if buy_or_sell == "BUY" else "S"
    typ = "MKT" if order_type == "MARKET" else "LMT"
    
    try:
        order_id = api.place_order(
            buy_or_sell=side, 
            product_type="I", 
            exchange="NFO",
            tradingsymbol=instrument, 
            quantity=qty, 
            discloseqty=qty,
            price_type=typ, 
            price=price, 
            trigger_price=price,
            amo=amo, 
            retention="DAY"
        )
        return order_id['norenordno']
    except Exception as e:
        print(f"[REJECTED] Order failed for {instrument}: {e}")
        return -1

def getLTP(exchange, symbol):
    """
    Get LTP for an instrument. 
    Can handle Shoonya Bridge on localhost:4002 or direct API calls.
    """
    # Prefer direct API for production hardened system
    try:
        res = api.get_quotes(exchange=exchange, token=symbol)
        if res and 'lp' in res:
            return float(res['lp'])
    except:
        pass
        
    # Fallback/Alternative: Bridge if direct fails or configured specifically
    try:
        url = f"http://localhost:4002/ltp?instrument={exchange}|{symbol}"
        resp = requests.get(url, timeout=3)
        data = resp.json()
        if isinstance(data, dict):
            return float(data.get("ltp", -1.0))
        return float(data)
    except:
        return -1.0
