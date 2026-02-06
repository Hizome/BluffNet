#!/bin/bash

# Kill any existing processes on ports 8000 (backend) and 5173 (frontend)
fuser -k 8000/tcp 2>/dev/null
fuser -k 5173/tcp 2>/dev/null

echo "🃏 Starting BluffNet..."

# Start Backend
echo "Starting Backend..."
cd backend
source venv/bin/activate
nohup uvicorn main:app --reload --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend running (PID: $BACKEND_PID). Logs: backend.log"

# Start Frontend
echo "Starting Frontend..."
cd ../frontend
nohup npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend running (PID: $FRONTEND_PID). Logs: frontend.log"

echo "✅ System started!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop both."

# Trap Ctrl+C to kill both processes
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT

wait
