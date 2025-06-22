# Entrypoint for the VITA Discord AI Knowledge Assistant 
import multiprocessing
import os
import signal
import sys
import time

def run_backend():
    import uvicorn
    uvicorn.run("src.backend.api:app", host="0.0.0.0", port=8000, reload=False)

def run_bot():
    import src.bot.discord_bot

def main():
    backend_proc = multiprocessing.Process(target=run_backend)
    bot_proc = multiprocessing.Process(target=run_bot)
    backend_proc.start()
    bot_proc.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        backend_proc.terminate()
        bot_proc.terminate()
        backend_proc.join()
        bot_proc.join()
        sys.exit(0)

if __name__ == "__main__":
    main()

# To run the bot, use:
# python -m src.bot.discord_bot
# To run the backend and scheduler, use:
# python -m src.main 