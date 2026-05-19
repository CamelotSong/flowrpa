# FlowRPA

<p align="center">
  <img src="docs/logo.png" alt="FlowRPA" width="120">
</p>

A cross-platform (Mac/Windows) RPA tool based on [DrissionPage](https://github.com/g1879/DrissionPage), featuring:

- 🎨 **Visual Workflow Editor** — Drag-and-drop node canvas to build automation flows
- 🤖 **Natural Language to Workflow** — Describe what you want, AI generates the flow
- 🎯 **Element Picker** — Chrome extension to select page elements with one click
- 🪟 **Liquid Glass Console** — Beautiful real-time execution dashboard
- 🔄 **DrissionPage Powered** — Robust browser control under the hood

## Architecture

```
Electron (Desktop UI)  ←→  Python Engine (DrissionPage)  ←→  Chrome Extension (Element Picker)
         WebSocket                    Native Messaging
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Chrome / Edge browser

### Install & Run

```bash
# Clone
git clone https://github.com/CamelotSong/flowrpa.git
cd flowrpa

# Setup Python engine
cd engine
pip install -r requirements.txt
python main.py

# Setup Desktop app
cd desktop
npm install
npm run dev

# Install Chrome Extension
# Load extension/ as unpacked extension in chrome://extensions
```

## Tech Stack

| Module | Technology |
|--------|-----------|
| Desktop UI | Electron + React + TypeScript |
| Workflow Canvas | React Flow |
| UI Framework | Ant Design |
| Liquid Glass | CSS backdrop-filter + custom shaders |
| RPA Engine | Python + DrissionPage |
| Communication | WebSocket + Native Messaging |
| AI | Configurable LLM API (OpenAI / Claude / ...) |

## License

MIT