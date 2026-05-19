import { app, BrowserWindow, ipcMain, shell } from 'electron'
import { spawn, ChildProcess } from 'child_process'
import * as path from 'path'
import * as fs from 'fs'

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged

let mainWindow: BrowserWindow | null = null
let engineProcess: ChildProcess | null = null

// ── Engine 启动 ──

function startEngine() {
  // 查找 Python 和引擎入口
  const engineDir = app.isPackaged
    ? path.join(process.resourcesPath, 'engine')
    : path.join(__dirname, '../../engine')

  const mainPy = path.join(engineDir, 'main.py')

  if (!fs.existsSync(mainPy)) {
    console.warn('[Engine] main.py not found at:', mainPy)
    return
  }

  const pythonCmds = ['python3', 'python']
  let started = false

  for (const cmd of pythonCmds) {
    try {
      engineProcess = spawn(cmd, [mainPy], {
        cwd: engineDir,
        stdio: ['ignore', 'pipe', 'pipe'],
        env: { ...process.env, PYTHONUNBUFFERED: '1' },
      })

      engineProcess.stdout?.on('data', (data: Buffer) => {
        console.log('[Engine]', data.toString().trim())
        mainWindow?.webContents.send('engine-log', data.toString())
      })

      engineProcess.stderr?.on('data', (data: Buffer) => {
        console.error('[Engine]', data.toString().trim())
        mainWindow?.webContents.send('engine-log', `[ERROR] ${data.toString()}`)
      })

      engineProcess.on('exit', (code) => {
        console.log('[Engine] Process exited with code:', code)
        mainWindow?.webContents.send('engine-status', { running: false, exitCode: code })
      })

      console.log('[Engine] Started with PID:', engineProcess.pid)
      started = true
      break
    } catch (e) {
      console.warn('[Engine] Failed to start with', cmd, e)
    }
  }

  if (!started) {
    console.error('[Engine] Could not start Python engine')
  }
}

function stopEngine() {
  if (engineProcess) {
    engineProcess.kill('SIGTERM')
    setTimeout(() => {
      if (engineProcess && !engineProcess.killed) {
        engineProcess.kill('SIGKILL')
      }
    }, 3000)
    engineProcess = null
  }
}

// ── Window 创建 ──

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    frame: false,
    // Mac 液态玻璃效果
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'hidden',
    vibrancy: process.platform === 'darwin' ? 'under-window' : undefined,
    visualEffectState: process.platform === 'darwin' ? 'active' : undefined,
    transparent: process.platform === 'darwin',
    backgroundColor: process.platform === 'darwin' ? '#00000000' : '#0f0f14',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
    },
    icon: path.join(__dirname, '../../public/logo.png'),
    show: false,
  })

  // 加载页面
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show()
  })

  // 外部链接用浏览器打开
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// ── IPC ──

ipcMain.handle('engine-status', async () => {
  return {
    running: engineProcess !== null && !engineProcess.killed,
    pid: engineProcess?.pid,
  }
})

ipcMain.handle('engine-restart', async () => {
  stopEngine()
  setTimeout(startEngine, 500)
  return { ok: true }
})

ipcMain.on('window-minimize', () => mainWindow?.minimize())
ipcMain.on('window-maximize', () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize()
  } else {
    mainWindow?.maximize()
  }
})
ipcMain.on('window-close', () => mainWindow?.close())

// ── App 生命周期 ──

app.whenReady().then(() => {
  createWindow()
  startEngine()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  stopEngine()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  stopEngine()
})
