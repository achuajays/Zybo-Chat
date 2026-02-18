# Zybo Chat 💬

> A real-time private messaging app built with Django Channels and WebSockets — featuring live online presence, typing indicators, read receipts, and message deletion.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django&logoColor=white)
![Channels](https://img.shields.io/badge/Django_Channels-4.2-092E20?style=for-the-badge&logo=django&logoColor=white)
![Daphne](https://img.shields.io/badge/Daphne-ASGI-FF6B35?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-Deployed-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 **Email Authentication** | Register and login with email + password |
| 🟢 **Live Online Status** | Green dot updates in real-time across all pages |
| 💬 **Private Chat** | One-on-one real-time messaging via WebSockets |
| ✓✓ **Read Receipts** | Single tick (sent) → double tick (read) |
| ⌨️ **Typing Indicator** | Animated 3-dot bubble when the other user types |
| 🔢 **Unread Count Badges** | Shows unread message count on user cards |
| 🗑️ **Delete Messages** | Hover to delete your own messages for both users |
| 📜 **Message History** | Full conversation history loaded on open |

---

## 🏗️ Architecture

```mermaid
graph TB
    subgraph Client["🌐 Browser (Client)"]
        UI["HTML/CSS/JS UI"]
        WS_Chat["WebSocket\n/ws/chat/&lt;id&gt;/"]
        WS_Status["WebSocket\n/ws/status/"]
    end

    subgraph Railway["☁️ Railway (Production)"]
        subgraph ASGI["Daphne ASGI Server"]
            Router["ProtocolTypeRouter"]
        end

        subgraph Django["Django Application"]
            Auth["AuthMiddlewareStack"]
            URLRouter["URLRouter"]

            subgraph Consumers["WebSocket Consumers"]
                ChatConsumer["ChatConsumer\n• connect/disconnect\n• chat_message\n• typing_indicator\n• delete_message\n• mark_read"]
                StatusConsumer["OnlineStatusConsumer\n• connect/disconnect\n• user_status broadcast"]
            end

            subgraph Views["HTTP Views"]
                LoginView["login_view"]
                RegisterView["register_view"]
                UserListView["user_list_view\n(unread counts)"]
                ChatView["chat_view\n(message history)"]
                LogoutView["logout_view"]
            end

            subgraph Signals["Django Signals"]
                LoginSignal["user_logged_in\n→ is_online=True"]
                LogoutSignal["user_logged_out\n→ is_online=False"]
            end
        end

        subgraph ChannelLayer["Channel Layer"]
            InMemory["InMemoryChannelLayer\n(dev/single-instance)"]
            Groups["Groups\n• chat_&lt;id1&gt;_&lt;id2&gt;\n• online_status"]
        end

        subgraph DB["SQLite Database /data/db.sqlite3"]
            UserModel["User\n• email (auth)\n• username\n• is_online\n• last_seen"]
            MessageModel["Message\n• sender FK\n• receiver FK\n• content\n• timestamp\n• is_read"]
        end

        subgraph Static["Static Files"]
            WhiteNoise["WhiteNoise\nCompressed + Cached"]
            CSS["style.css\n(Scandinavian theme)"]
        end
    end

    UI -->|"HTTP"| Router
    WS_Chat -->|"WebSocket Upgrade"| Router
    WS_Status -->|"WebSocket Upgrade"| Router

    Router -->|"http"| Views
    Router -->|"websocket"| Auth
    Auth --> URLRouter
    URLRouter --> ChatConsumer
    URLRouter --> StatusConsumer

    ChatConsumer <-->|"group_send/receive"| InMemory
    StatusConsumer <-->|"group_send/receive"| InMemory
    InMemory --> Groups

    ChatConsumer -->|"save/read"| MessageModel
    ChatConsumer -->|"update status"| UserModel
    StatusConsumer -->|"update status"| UserModel

    Views -->|"query"| UserModel
    Views -->|"query"| MessageModel

    LoginSignal -->|"update"| UserModel
    LogoutSignal -->|"update"| UserModel

    WhiteNoise --> CSS

    style Client fill:#E8F5E9,stroke:#4CAF50
    style Railway fill:#E3F2FD,stroke:#2196F3
    style Consumers fill:#FFF3E0,stroke:#FF9800
    style DB fill:#FCE4EC,stroke:#E91E63
    style ChannelLayer fill:#F3E5F5,stroke:#9C27B0
```

### WebSocket Message Flow

```mermaid
sequenceDiagram
    participant A as User A (Sender)
    participant S as Django Server
    participant CL as Channel Layer
    participant B as User B (Receiver)

    A->>S: WS Connect /ws/chat/B_id/
    S->>CL: group_add(chat_A_B, channel_A)
    B->>S: WS Connect /ws/chat/A_id/
    S->>CL: group_add(chat_A_B, channel_B)

    Note over A,B: Both users in same room group

    A->>S: {type: "typing", is_typing: true}
    S->>CL: group_send(chat_A_B, typing_indicator)
    CL->>B: {type: "typing_indicator", sender_id: A, is_typing: true}
    B-->>B: Show animated dots

    A->>S: {type: "chat_message", message: "Hello!"}
    S->>S: save_message() → DB
    S->>CL: group_send(chat_A_B, chat_message)
    CL->>A: {type: "chat_message", message_id: 42, ...}
    CL->>B: {type: "chat_message", message_id: 42, ...}
    A-->>A: Append bubble (sent ✓)
    B-->>B: Append bubble (received)

    B->>S: {type: "mark_read"}
    S->>S: mark_messages_read() → DB
    S->>CL: group_send(chat_A_B, messages_read)
    CL->>A: {type: "messages_read", reader_id: B}
    A-->>A: Update ✓ → ✓✓

    A->>S: {type: "delete_message", message_id: 42}
    S->>S: delete_message() → DB (only if sender)
    S->>CL: group_send(chat_A_B, message_deleted)
    CL->>A: {type: "message_deleted", message_id: 42}
    CL->>B: {type: "message_deleted", message_id: 42}
    A-->>A: Replace with "🗑 Message deleted"
    B-->>B: Replace with "🗑 Message deleted"
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) package manager

### 1. Clone the repository

```bash
git clone https://github.com/your-username/zybo.git
cd zybo
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Apply database migrations

```bash
uv run python manage.py migrate
```

### 4. Create a superuser (optional)

```bash
uv run python manage.py createsuperuser
```

### 5. Run the development server

```bash
uv run python manage.py runserver
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

> **Note:** The dev server uses Django's built-in ASGI runner which supports WebSockets. No separate Daphne process needed locally.

---

## 🐳 Docker

### Build and run locally

```bash
docker build -t zybo .
docker run -p 8000:8000 \
  -e SECRET_KEY=your-secret-key \
  -e DEBUG=False \
  -e ALLOWED_HOSTS=* \
  -e DB_PATH=/data/db.sqlite3 \
  -v zybo_data:/data \
  zybo
```

Open [http://localhost:8000](http://localhost:8000).

---

## ☁️ Deploy to Railway

### 1. Push your code to GitHub

```bash
git add .
git commit -m "Initial commit"
git push origin main
```

### 2. Create a new Railway project

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Select your repository

### 3. Set environment variables

In Railway → your service → **Variables**, add:

| Variable | Value |
|---|---|
| `SECRET_KEY` | Generate with: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `*` |
| `DB_PATH` | `/data/db.sqlite3` |

### 4. Deploy

Railway will automatically detect the `Dockerfile` and `railway.json`, build the image, run migrations, and start Daphne on port 8000.

---

## 📁 Project Structure

```
zybo/
├── config/
│   ├── settings.py        # Django settings (env-var driven)
│   ├── asgi.py            # ASGI config with Channels routing
│   └── urls.py            # Root URL configuration
├── core/
│   ├── consumers.py       # WebSocket consumers (Chat + OnlineStatus)
│   ├── models.py          # User & Message models + signals
│   ├── views.py           # HTTP views (login, register, chat, users)
│   ├── routing.py         # WebSocket URL patterns
│   ├── backends.py        # Email authentication backend
│   ├── forms.py           # Registration & login forms
│   ├── templatetags/
│   │   └── chat_tags.py   # Avatar color & initials template tags
│   └── templates/core/
│       ├── base.html      # Base template (global WS presence)
│       ├── login.html
│       ├── register.html
│       ├── user_list.html # People page with unread badges
│       └── chat.html      # Chat interface
├── static/css/
│   └── style.css          # Warm Scandinavian Minimal theme
├── Dockerfile             # Multi-stage production build
├── entrypoint.sh          # migrate → daphne startup script
├── railway.json           # Railway deployment config
└── pyproject.toml         # Dependencies (uv)
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Django 5.2 |
| **WebSockets** | Django Channels 4.2 |
| **ASGI Server** | Daphne 4.1 |
| **Channel Layer** | In-Memory (single instance) |
| **Database** | SQLite |
| **Static Files** | WhiteNoise |
| **Package Manager** | uv |
| **Containerization** | Docker (multi-stage) |
| **Deployment** | Railway |

---

## 📄 License

MIT
