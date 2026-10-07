"""Exercise the durable batch flow through the frontend proxy."""
import sys
from batch_smoke import main

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080")
