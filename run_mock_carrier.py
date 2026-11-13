"""Run the local mock carrier endpoint on 127.0.0.1:8010."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("services.mock_carrier_api:app", host="127.0.0.1", port=8010, reload=False)
