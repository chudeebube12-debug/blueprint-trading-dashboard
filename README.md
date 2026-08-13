---
Deploying frontend and backend as two Heroku apps (recommended)

1. Create two Heroku apps (one for frontend, one for backend)
- heroku create my-deriv-frontend
- heroku create my-deriv-backend

2. Add remotes (if create didn't already add them)
- git remote add heroku-frontend https://git.heroku.com/my-deriv-frontend.git
- git remote add heroku-backend  https://git.heroku.com/my-deriv-backend.git

3. Ensure Procfiles are in the subfolders:
- frontend/Procfile -> web: node server.js
- backend/Procfile  -> web: gunicorn app:app
                       worker: python worker.py

4. Commit the new files
- git add frontend/Procfile backend/Procfile backend/worker.py README.md
- git commit -m "Add Heroku Procfiles, worker and deploy docs"

5. Push each subfolder to its Heroku app using git subtree (from repo root)
- git subtree push --prefix frontend heroku-frontend main
- git subtree push --prefix backend  heroku-backend  main
(If your default branch is master, replace main with master.)

6. Configure backend environment (API token)
- heroku config:set API_TOKEN=your_token_here --app my-deriv-backend

7. Scale the worker (to run background streaming)
- heroku ps:scale worker=1 --app my-deriv-backend

8. Logs and debugging
- heroku logs --tail --app my-deriv-backend
- heroku open --app my-deriv-frontend

Notes
- The worker.py is a placeholder. Replace the loop with actual Deriv WebSocket/streaming code and add reconnection, error handling, and rate-limit logic.
- Ensure backend/requirements.txt includes any websocket library you use (e.g., websocket-client or websockets) and gunicorn.
- Keep API_TOKEN in Heroku config (do not commit tokens to source).
- If your frontend needs an npm build step, keep it as a separate Node app and deploy as the frontend Heroku app.
