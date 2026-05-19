"""stealth.py - DrissionPage 反检测配置

注入各类 JS 补丁，欺骗常见的反爬检测指标：
- navigator.webdriver
- plugins/languages
- Canvas/WebGL 指纹随机化
- 随机 User-Agent
"""

import random
import string
from typing import Optional


# 真实浏览器 UA 池
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

SCREEN_RESOLUTIONS = [
    (1920, 1080), (2560, 1440), (1440, 900), (1680, 1050),
    (1366, 768), (2560, 1600), (1920, 1200), (3840, 2160),
]

# Canvas 指纹随机化 JS 补丁
CANVAS_FINGERPRINT_PATCH = """
(function() {
  const originalGetContext = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function(type, ...args) {
    const ctx = originalGetContext.apply(this, [type, ...args]);
    if (!ctx) return ctx;
    if (type === '2d') {
      const originalFillText = ctx.fillText.bind(ctx);
      ctx.fillText = function(text, x, y, ...rest) {
        x += Math.random() * 0.1 - 0.05;
        y += Math.random() * 0.1 - 0.05;
        return originalFillText(text, x, y, ...rest);
      };
      const originalGetImageData = ctx.getImageData.bind(ctx);
      ctx.getImageData = function(sx, sy, sw, sh) {
        const imageData = originalGetImageData(sx, sy, sw, sh);
        for (let i = 0; i < imageData.data.length; i += 100) {
          imageData.data[i] = imageData.data[i] ^ (Math.random() * 2 | 0);
        }
        return imageData;
      };
    }
    return ctx;
  };

  // toDataURL 随机化
  const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
  HTMLCanvasElement.prototype.toDataURL = function(type, quality) {
    if (this.width === 0 || this.height === 0) return originalToDataURL.apply(this, arguments);
    const ctx = originalGetContext.apply(this, ['2d']);
    if (ctx) {
      const imageData = ctx.getImageData(0, 0, this.width, this.height);
      const pixelIndex = Math.floor(Math.random() * imageData.data.length / 4) * 4;
      const originalValue = imageData.data[pixelIndex];
      imageData.data[pixelIndex] = originalValue ^ 1;
      ctx.putImageData(imageData, 0, 0);
      const result = originalToDataURL.apply(this, arguments);
      imageData.data[pixelIndex] = originalValue;
      ctx.putImageData(imageData, 0, 0);
      return result;
    }
    return originalToDataURL.apply(this, arguments);
  };
})();
"""

# WebGL 指纹随机化 JS 补丁
WEBGL_FINGERPRINT_PATCH = """
(function() {
  const getParameter = WebGLRenderingContext.prototype.getParameter;
  WebGLRenderingContext.prototype.getParameter = function(parameter) {
    // UNMASKED_VENDOR_WEBGL = 37445, UNMASKED_RENDERER_WEBGL = 37446
    if (parameter === 37445) {
      return 'Intel Inc.';
    }
    if (parameter === 37446) {
      const renderers = [
        'Intel Iris OpenGL Engine',
        'Intel(R) UHD Graphics 630',
        'ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)',
        'Apple M1'
      ];
      return renderers[Math.floor(Math.random() * renderers.length)];
    }
    return getParameter.apply(this, arguments);
  };

  // WebGL2
  if (typeof WebGL2RenderingContext !== 'undefined') {
    const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
    WebGL2RenderingContext.prototype.getParameter = function(parameter) {
      if (parameter === 37445) return 'Intel Inc.';
      if (parameter === 37446) return 'Intel Iris OpenGL Engine';
      return getParameter2.apply(this, arguments);
    };
  }
})();
"""

# 核心反检测 JS 补丁
WEBDRIVER_PATCH = """
Object.defineProperty(navigator, 'webdriver', {
  get: () => false,
  configurable: true
});
"""

CHROME_PATCH = """
(function() {
  // 让 window.chrome 看起来正常
  if (!window.chrome) {
    window.chrome = {
      app: { isInstalled: false },
      runtime: {
        onMessage: { addListener: function(){}, removeListener: function(){} },
        connect: function(){},
        sendMessage: function(){},
        id: undefined
      },
      loadTimes: function(){},
      csi: function(){ return {}; }
    };
  }

  // 修复 navigator.plugins（非空）
  const pluginData = [
    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
    { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }
  ];
  const pluginArray = pluginData.map(p => {
    const plugin = Object.create(Plugin.prototype);
    Object.defineProperties(plugin, {
      0: { value: { type: 'application/x-google-chrome-pdf' }, enumerable: true },
      name: { value: p.name, enumerable: true },
      filename: { value: p.filename, enumerable: true },
      description: { value: p.description, enumerable: true },
      length: { value: 1, enumerable: true }
    });
    return plugin;
  });
  Object.defineProperty(navigator, 'plugins', { get: () => pluginArray });

  // 修复 navigator.languages
  Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en-US', 'en'] });

  // 修复 Notification.permission
  if (typeof Notification !== 'undefined') {
    Object.defineProperty(Notification, 'permission', { get: () => 'default' });
  }

  // 修复 permissions
  const originalQuery = navigator.permissions && navigator.permissions.query;
  if (originalQuery) {
    navigator.permissions.query = (params) => {
      if (params.name === 'notifications') {
        return Promise.resolve({ state: Notification.permission });
      }
      return originalQuery.apply(navigator.permissions, [params]);
    };
  }
})();
"""


def get_stealth_options(user_agent: Optional[str] = None):
    """获取带反检测配置的 ChromiumOptions

    Returns:
        ChromiumOptions 实例
    """
    try:
        from DrissionPage import ChromiumOptions
    except ImportError:
        raise ImportError("请先安装 DrissionPage: pip install DrissionPage")

    co = ChromiumOptions()

    # 随机 User-Agent
    ua = user_agent or random.choice(USER_AGENTS)
    co.set_user_agent(ua)

    # 基础隐身参数
    co.set_argument("--disable-blink-features=AutomationControlled")
    co.set_argument("--disable-infobars")
    co.set_argument("--no-first-run")
    co.set_argument("--no-service-autorun")
    co.set_argument("--no-default-browser-check")
    co.set_argument("--disable-web-security")
    co.set_argument("--allow-running-insecure-content")
    co.set_argument("--disable-client-side-phishing-detection")
    co.set_argument("--disable-popup-blocking")
    co.set_argument("--ignore-certificate-errors")
    co.set_argument("--disable-extensions-http-throttling")
    co.set_argument("--password-store=basic")
    co.set_argument("--use-mock-keychain")

    # 排除自动化扩展标志
    co.set_argument("--exclude-switches=enable-automation")
    co.set_argument("--disable-automation")

    # 随机窗口大小
    w, h = random.choice(SCREEN_RESOLUTIONS)
    co.set_argument(f"--window-size={w},{h}")

    # 禁用通知、密码保存弹窗
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_setting_values.geolocation": 2,
    }
    co.set_pref("excludeSwitches", ["enable-automation"])
    for k, v in prefs.items():
        co.set_pref(k, v)

    # 注入 JS 补丁（在每个页面加载前执行）
    all_patches = "\n".join([
        WEBDRIVER_PATCH,
        CHROME_PATCH,
        CANVAS_FINGERPRINT_PATCH,
        WEBGL_FINGERPRINT_PATCH,
    ])
    co.set_argument(f"--user-data-dir=")  # 不持久化 profile（每次干净启动）

    return co


def inject_stealth_scripts(page):
    """向已打开的页面注入反检测脚本（补充 DrissionPage 的内置补丁之外的部分）"""
    all_patches = "\n".join([
        WEBDRIVER_PATCH,
        CHROME_PATCH,
        CANVAS_FINGERPRINT_PATCH,
        WEBGL_FINGERPRINT_PATCH,
    ])
    try:
        page.run_js(all_patches)
    except Exception:
        pass
