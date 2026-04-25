import os
import sys
# Add project root and shared dir to sys.path
sys.path.append("/home/algo/ThetaEdge")
sys.path.append("/home/algo/ThetaEdge/shared")
from shared.NorenApi import NorenApi
import inspect

def inspect_api():
    print("Inspecting NorenApi.get_time_price_series...")
    sig = inspect.signature(NorenApi.get_time_price_series)
    print(f"Signature: {sig}")

if __name__ == "__main__":
    inspect_api()
