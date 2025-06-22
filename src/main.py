# Entrypoint for the VITA Discord AI Knowledge Assistant 
import sys
import uvicorn
from src.backend.api import app
from src.backend.decay import scheduler, run_decay_job

# macOS SSL certificate check
if sys.platform == "darwin":
    import ssl
    try:
        ssl.create_default_context().load_verify_locations(capath=None, cafile=None)
    except Exception:
        print("\n[WARNING] SSL certificate verification may fail on macOS. If you see SSL errors, run:")
        print("/Applications/Python 3.11/Install Certificates.command\n")

if __name__ == "__main__":
    # Start decay/archival scheduler
    scheduler.add_job(run_decay_job, 'interval', days=1)
    scheduler.start()
    # Start FastAPI backend
    uvicorn.run(app, host="0.0.0.0", port=8001)

# To run the bot, use:
# python -m src.bot.discord_bot
# To run the backend and scheduler, use:
# python -m src.main 