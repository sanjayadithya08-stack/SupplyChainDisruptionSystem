import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("Initializing TechCore 2026 SupplyChain Database...")

from db.reseed_db import reseed
reseed()

print("\nDatabase initialized and seeded successfully!")

