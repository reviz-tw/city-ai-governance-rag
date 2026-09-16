"""Local-only development server with a signing key kept in process memory."""
import os
import secrets
import uvicorn

if __name__=='__main__':
    os.environ.setdefault('AUTH_SESSION_SECRET',secrets.token_urlsafe(48))
    uvicorn.run('app.main:app',host='127.0.0.1',port=8080,reload=True,reload_dirs=['backend/app'])
