# 📅 Evolution API - Appointment Scheduler

A REST API for automated appointment scheduling via WhatsApp, powered by AI.

---

## 🚀 What this project does

- Automates appointment scheduling via WhatsApp messages
- Uses AI to interpret user requests
- Stores appointments and client data in a local database
- Can be containerized with Docker for easy deployment

---

## 📁 Project Structure
.
├── sistema_agendamento.py # Main application code
├── requirements.txt # Python dependencies
├── Dockerfile # Docker configuration
├── render.yaml # Deployment config for Render
└── README.md # This file

---

## 🧩 Technologies Used

- Python 3.10+
- SQLite
- Docker
- AI integration (user-defined)
- REST API (FastAPI or Flask)

---

## 📦 How to Run

### Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/alictech7-oss/evolution_api.git
cd evolution_api

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python sistema_agendamento.py

Docker Setup
# 1. Build the image
docker build -t evolution-api .

# 2. Run the container
docker run -p 8080:8080 evolution-api

🔑 Environment Variables
The application uses a .env file or environment variables for configuration:

. AUTHENTICATION_API_KEY: API key for authentication

. SERVER_URL: Public URL where the service is hosted

🚀 Deployment
This project includes a render.yaml file for easy deployment on Render.

1. Connect your GitHub repository to Render.

1. Select the "Blueprint" or "Web Service" option.

3. Render will automatically detect the configuration and deploy your service.

📌 Notes
. The main logic for appointment handling is in sistema_agendamento.py.

. The project is designed to be modular and easily extendable.

🙏 Credits & Original Work
This project was developed by alictech7-oss as a practical solution for automated scheduling.

📄 License
MIT — use, modify, and share freely.


requests
python-dotenv


