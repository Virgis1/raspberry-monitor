# Raspberry Monitor

A lightweight web dashboard for monitoring and managing services running on a Raspberry Pi.

I built this project for my own Raspberry Pi server to have one place where I can check system health, monitor applications and Docker containers, restart services and receive alerts when something goes wrong.

## Features

- CPU usage monitoring
- CPU temperature monitoring
- RAM usage monitoring
- system disk usage
- external SSD monitoring
- system uptime
- top processes by CPU usage
- systemd service monitoring
- Docker container monitoring
- start, stop and restart services
- Raspberry Pi shutdown from the dashboard
- high CPU usage alerts
- high temperature alerts
- SSD disconnect alerts
- service status notifications
- secure remote access through Cloudflare Tunnel

## Tech stack

### Backend
- Python
- FastAPI
- Uvicorn
- psutil
- requests

### Frontend
- React
- TypeScript
- Vite

### Infrastructure
- Raspberry Pi
- Linux
- systemd
- Docker
- Cloudflare Tunnel
- Cloudflare Access
- ntfy

## Project structure

```text
raspberry-monitor/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── .gitignore
└── README.md
```

## How it works

```text
Browser
   |
   | HTTPS
   v
Cloudflare Access
   |
Cloudflare Tunnel
   |
   +-- /        -> React frontend
   |
   +-- /api/*   -> FastAPI backend
                       |
                       +-- psutil
                       +-- systemd
                       +-- Docker
```

The React frontend displays system information and service status.

The FastAPI backend collects system information from the Raspberry Pi and provides API endpoints for monitoring and managing selected systemd services and Docker containers.

## Local development

### Backend

Create a virtual environment:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file based on `.env.example`.

Start the backend:

```bash
uvicorn main:app --host 0.0.0.0 --port 8200
```

### Frontend

Install dependencies:

```bash
cd frontend
npm install
```

Start the development server:

```bash
npm run dev
```

## Deployment

The application currently runs on my own Raspberry Pi server.

The backend and frontend are managed as systemd services and start automatically after a Raspberry Pi reboot.

Remote access is provided through Cloudflare Tunnel.

The dashboard is protected with Cloudflare Access authentication, so application ports do not need to be exposed directly to the public internet.

## Notifications

The backend can send notifications through ntfy when important events occur.

Examples:

- external SSD disconnected
- external SSD reconnected
- high CPU usage
- CPU usage returned to normal
- high CPU temperature
- CPU temperature returned to normal
- monitored systemd service stopped
- monitored systemd service recovered
- monitored Docker container stopped
- monitored Docker container recovered

The ntfy topic is stored in an environment variable and is not included in the repository.

Example `.env.example`:

```env
NTFY_TOPIC=your-private-topic
```

## Security

Sensitive configuration is not stored in this repository.

Do not commit:

- `.env` files
- API keys
- passwords
- Cloudflare credentials
- SSH keys
- private ntfy topics
- database files
- personal files or photos

Cloudflare Tunnel credentials and production server configuration should remain outside the repository.

## Why I built it

I run several applications on a Raspberry Pi and wanted a simple dashboard where I could see the state of the server without connecting through SSH every time.

The project also gave me practical experience with:

- Python and FastAPI
- React and TypeScript
- REST APIs
- Linux and systemd
- Docker
- server monitoring
- notifications
- secure remote access
