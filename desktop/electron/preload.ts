import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('flowrpa', {
  // Engine
  getEngineStatus: () => ipcRenderer.invoke('engine-status'),
  restartEngine: () => ipcRenderer.invoke('engine-restart'),

  // Engine events
  onEngineLog: (callback: (data: string) => void) => {
    const handler = (_event: any, data: string) => callback(data)
    ipcRenderer.on('engine-log', handler)
    return () => ipcRenderer.removeListener('engine-log', handler)
  },
  onEngineStatus: (callback: (data: any) => void) => {
    const handler = (_event: any, data: any) => callback(data)
    ipcRenderer.on('engine-status', handler)
    return () => ipcRenderer.removeListener('engine-status', handler)
  },

  // Window controls
  minimizeWindow: () => ipcRenderer.send('window-minimize'),
  maximizeWindow: () => ipcRenderer.send('window-maximize'),
  closeWindow: () => ipcRenderer.send('window-close'),

  // Platform info
  platform: process.platform,
})
