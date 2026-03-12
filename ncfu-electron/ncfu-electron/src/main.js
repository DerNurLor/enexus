const { app, BrowserWindow, WebContentsView, ipcMain, shell, Menu, Tray, nativeImage, session } = require('electron')
const path = require('path')

const APP_URL  = 'https://app.enexus.isabelline.xyz'
const APP_NAME = 'НЦФУ'
const TITLEBAR_H = 38

let mainWindow = null
let webView    = null
let tray       = null

// ── Create main window ────────────────────────────────────────────────────────

function createWindow() {
  mainWindow = new BrowserWindow({
    width:     1100,
    height:    740,
    minWidth:  480,
    minHeight: 600,
    title:     APP_NAME,
    icon:      getIcon(),
    frame:     false,
    backgroundColor: '#0a0a0a',
    webPreferences: {
      nodeIntegration:  false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    show: false,
  })

  mainWindow.loadFile(path.join(__dirname, 'index.html'))

  // Attach WebContentsView for the site
  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
    createWebView()
  })

  mainWindow.on('resize', () => repositionWebView())

  mainWindow.on('close', (e) => {
    if (process.platform === 'darwin') {
      e.preventDefault()
      mainWindow.hide()
    }
  })
}

// ── WebContentsView (replaces old BrowserView / webview tag) ─────────────────

function createWebView() {
  webView = new WebContentsView({
    webPreferences: {
      nodeIntegration:  false,
      contextIsolation: true,
      partition: 'persist:ncfu',
    }
  })

  mainWindow.contentView.addChildView(webView)
  repositionWebView()

  webView.webContents.loadURL(APP_URL + '/schedule')

  // Forward loading events to renderer
  webView.webContents.on('did-start-loading', () => {
    mainWindow.webContents.send('loading-start')
  })
  webView.webContents.on('did-stop-loading', () => {
    mainWindow.webContents.send('loading-stop')
    const url = webView.webContents.getURL()
    mainWindow.webContents.send('url-changed', url)
  })
  webView.webContents.on('did-navigate', (_, url) => {
    mainWindow.webContents.send('url-changed', url)
  })
  webView.webContents.on('did-navigate-in-page', (_, url) => {
    mainWindow.webContents.send('url-changed', url)
  })
  webView.webContents.on('did-fail-load', (_, code) => {
    if (code === -3) return // aborted
    mainWindow.webContents.send('load-failed')
  })

  // Open external links in browser
  webView.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })
}

function repositionWebView() {
  if (!webView || !mainWindow) return
  const [w, h] = mainWindow.getContentSize()
  webView.setBounds({ x: 0, y: TITLEBAR_H, width: w, height: h - TITLEBAR_H })
}

// ── Tray ──────────────────────────────────────────────────────────────────────

function createTray() {
  try {
    const icon = nativeImage.createFromPath(getIcon()).resize({ width: 16, height: 16 })
    tray = new Tray(icon)
  } catch {
    tray = new Tray(nativeImage.createEmpty())
  }

  tray.setToolTip(APP_NAME)
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: APP_NAME, enabled: false },
    { type: 'separator' },
    { label: 'Открыть',      click: () => { mainWindow?.show(); mainWindow?.focus() } },
    { label: 'Расписание',   click: () => navigateTo('/schedule') },
    { label: 'Профиль',      click: () => navigateTo('/profile') },
    { type: 'separator' },
    { label: 'Выход',        click: () => app.quit() },
  ]))

  tray.on('click', () => {
    mainWindow?.isVisible() ? mainWindow.hide() : mainWindow?.show()
  })
}

function navigateTo(path) {
  mainWindow?.show()
  mainWindow?.focus()
  webView?.webContents.loadURL(APP_URL + path)
  mainWindow?.webContents.send('url-changed', APP_URL + path)
}

// ── IPC ───────────────────────────────────────────────────────────────────────

ipcMain.on('window-minimize',  () => mainWindow?.minimize())
ipcMain.on('window-maximize',  () => mainWindow?.isMaximized() ? mainWindow.unmaximize() : mainWindow?.maximize())
ipcMain.on('window-close',     () => process.platform === 'darwin' ? mainWindow?.hide() : mainWindow?.close())
ipcMain.handle('is-maximized', () => mainWindow?.isMaximized() ?? false)

ipcMain.on('navigate', (_, p) => navigateTo(p))
ipcMain.on('reload',   ()     => webView?.webContents.reload())
ipcMain.on('go-back',  ()     => webView?.webContents.canGoBack()    && webView.webContents.goBack())
ipcMain.on('go-forward',()    => webView?.webContents.canGoForward() && webView.webContents.goForward())

// ── Icons ─────────────────────────────────────────────────────────────────────

function getIcon() {
  const a = path.join(__dirname, '..', 'assets')
  if (process.platform === 'win32')  return path.join(a, 'icon.ico')
  if (process.platform === 'darwin') return path.join(a, 'icon.icns')
  return path.join(a, 'icon.png')
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  createWindow()
  createTray()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
    else mainWindow?.show()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
