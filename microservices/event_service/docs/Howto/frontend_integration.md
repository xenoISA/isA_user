# 前端集成指南

## 概述

本指南基于真实测试的Event Service，提供前端JavaScript/TypeScript的完整集成方案。

## 核心JavaScript SDK

### 基础EventTracker类

```javascript
/**
 * Event Service 前端 SDK
 * 支持单个和批量事件采集
 */
class EventTracker {
  constructor(options = {}) {
    this.baseUrl = options.baseUrl || 'http://localhost:8230';
    this.userId = options.userId || null;
    this.sessionId = options.sessionId || this.generateSessionId();
    this.batchSize = options.batchSize || 10;
    this.batchTimeout = options.batchTimeout || 5000; // 5秒
    
    this.eventQueue = [];
    this.batchTimer = null;
    this.isOnline = navigator.onLine;
    
    this.initializeEventListeners();
    this.startBatchProcessor();
  }

  generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  initializeEventListeners() {
    // 网络状态监听
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.flushOfflineEvents();
    });
    
    window.addEventListener('offline', () => {
      this.isOnline = false;
    });

    // 页面卸载时发送剩余事件
    window.addEventListener('beforeunload', () => {
      this.flush(true); // 同步发送
    });
  }

  /**
   * 跟踪单个事件
   */
  async track(eventType, data = {}, options = {}) {
    const event = {
      event_type: eventType,
      category: options.category || 'user_interaction',
      page_url: window.location.href,
      user_id: this.userId,
      session_id: this.sessionId,
      data: {
        ...data,
        timestamp: new Date().toISOString(),
        page_title: document.title,
        referrer: document.referrer
      },
      metadata: {
        user_agent: navigator.userAgent,
        screen_resolution: `${screen.width}x${screen.height}`,
        viewport_size: `${window.innerWidth}x${window.innerHeight}`,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        language: navigator.language,
        ...options.metadata
      }
    };

    if (options.immediate) {
      return this.sendEvent(event);
    } else {
      this.addToQueue(event);
    }
  }

  /**
   * 添加到批量队列
   */
  addToQueue(event) {
    this.eventQueue.push(event);
    
    if (this.eventQueue.length >= this.batchSize) {
      this.flush();
    }
  }

  /**
   * 发送批量事件
   */
  async flush(sync = false) {
    if (this.eventQueue.length === 0) return;

    const eventsToSend = [...this.eventQueue];
    this.eventQueue = [];

    const batchData = {
      events: eventsToSend,
      client_info: {
        batch_timestamp: new Date().toISOString(),
        browser: this.getBrowserInfo(),
        device: this.getDeviceInfo(),
        connection: this.getConnectionInfo()
      }
    };

    if (sync) {
      // 同步发送（页面卸载时）
      navigator.sendBeacon(
        `${this.baseUrl}/api/frontend/events/batch`,
        JSON.stringify(batchData)
      );
    } else {
      return this.sendBatch(batchData);
    }
  }

  /**
   * 发送单个事件
   */
  async sendEvent(event) {
    if (!this.isOnline) {
      this.saveToLocalStorage([event]);
      return { status: 'queued_offline' };
    }

    try {
      const response = await fetch(`${this.baseUrl}/api/frontend/events`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(event)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.warn('Event tracking failed:', error);
      this.saveToLocalStorage([event]);
      return { status: 'error', error: error.message };
    }
  }

  /**
   * 发送批量事件
   */
  async sendBatch(batchData) {
    if (!this.isOnline) {
      this.saveToLocalStorage(batchData.events);
      return { status: 'queued_offline' };
    }

    try {
      const response = await fetch(`${this.baseUrl}/api/frontend/events/batch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(batchData)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.warn('Batch event tracking failed:', error);
      this.saveToLocalStorage(batchData.events);
      return { status: 'error', error: error.message };
    }
  }

  /**
   * 启动批量处理器
   */
  startBatchProcessor() {
    setInterval(() => {
      if (this.eventQueue.length > 0) {
        this.flush();
      }
    }, this.batchTimeout);
  }

  /**
   * 离线事件存储
   */
  saveToLocalStorage(events) {
    try {
      const stored = JSON.parse(localStorage.getItem('pending_events') || '[]');
      stored.push(...events);
      localStorage.setItem('pending_events', JSON.stringify(stored.slice(-100))); // 最多存储100个
    } catch (error) {
      console.warn('Failed to save events to localStorage:', error);
    }
  }

  /**
   * 恢复离线事件
   */
  async flushOfflineEvents() {
    try {
      const stored = JSON.parse(localStorage.getItem('pending_events') || '[]');
      if (stored.length > 0) {
        console.log(`Sending ${stored.length} offline events`);
        
        const batchData = {
          events: stored,
          client_info: {
            batch_timestamp: new Date().toISOString(),
            offline_recovery: true
          }
        };

        const result = await this.sendBatch(batchData);
        if (result.status === 'accepted') {
          localStorage.removeItem('pending_events');
        }
      }
    } catch (error) {
      console.warn('Failed to flush offline events:', error);
    }
  }

  /**
   * 工具方法
   */
  getBrowserInfo() {
    const ua = navigator.userAgent;
    let browser = 'Unknown';
    
    if (ua.includes('Chrome')) browser = 'Chrome';
    else if (ua.includes('Firefox')) browser = 'Firefox';
    else if (ua.includes('Safari')) browser = 'Safari';
    else if (ua.includes('Edge')) browser = 'Edge';
    
    return browser;
  }

  getDeviceInfo() {
    return {
      type: /Mobi|Android/i.test(navigator.userAgent) ? 'mobile' : 'desktop',
      platform: navigator.platform,
      memory: navigator.deviceMemory || 'unknown',
      cores: navigator.hardwareConcurrency || 'unknown'
    };
  }

  getConnectionInfo() {
    const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    return conn ? {
      type: conn.effectiveType,
      downlink: conn.downlink,
      rtt: conn.rtt
    } : null;
  }

  /**
   * 设置用户ID
   */
  setUserId(userId) {
    this.userId = userId;
  }

  /**
   * 更新会话ID
   */
  renewSession() {
    this.sessionId = this.generateSessionId();
  }
}
```

## 使用示例

### 基础初始化

```javascript
// 初始化事件跟踪器
const tracker = new EventTracker({
  baseUrl: 'https://api.example.com', // 生产环境URL
  userId: getCurrentUserId(), // 从你的认证系统获取
  batchSize: 10,
  batchTimeout: 5000
});

// 设置用户ID（登录后）
tracker.setUserId('user_12345');
```

### 页面浏览跟踪

```javascript
// 自动跟踪页面浏览
function trackPageView() {
  tracker.track('page_view', {
    page_title: document.title,
    page_url: window.location.href,
    load_time: performance.now(),
    referrer: document.referrer
  }, {
    category: 'user_interaction',
    immediate: false // 批量发送
  });
}

// 页面加载完成后跟踪
window.addEventListener('load', trackPageView);

// SPA路由变化跟踪
window.addEventListener('popstate', trackPageView);
```

### 用户交互跟踪

```javascript
// 按钮点击跟踪
document.addEventListener('click', (event) => {
  const button = event.target.closest('button, a[role="button"], .btn');
  if (button) {
    tracker.track('button_click', {
      button_id: button.id || null,
      button_text: button.textContent.trim().slice(0, 50),
      button_class: button.className,
      element_tag: button.tagName.toLowerCase(),
      position: {
        x: event.clientX,
        y: event.clientY
      }
    }, {
      category: 'user_interaction'
    });
  }
});

// 表单提交跟踪
document.addEventListener('submit', (event) => {
  const form = event.target;
  tracker.track('form_submit', {
    form_id: form.id || null,
    form_name: form.name || null,
    form_method: form.method || 'get',
    fields_count: form.elements.length,
    has_validation_errors: form.querySelector('.error, .invalid') !== null
  }, {
    category: 'business_action',
    immediate: true // 立即发送，因为页面可能会跳转
  });
});
```

### 业务事件跟踪

```javascript
// 购买完成
function trackPurchase(orderData) {
  tracker.track('purchase_completed', {
    order_id: orderData.id,
    total_amount: orderData.total,
    currency: orderData.currency,
    items_count: orderData.items.length,
    payment_method: orderData.paymentMethod,
    discount_applied: orderData.discount > 0
  }, {
    category: 'business_action',
    immediate: true
  });
}

// 用户注册
function trackRegistration(userData) {
  tracker.track('user_registered', {
    registration_method: userData.method, // email, social, phone
    account_type: userData.type,
    marketing_consent: userData.marketingConsent
  }, {
    category: 'business_action',
    immediate: true
  });
}
```

### 错误和性能跟踪

```javascript
// JavaScript错误跟踪
window.addEventListener('error', (event) => {
  tracker.track('js_error', {
    message: event.message,
    filename: event.filename,
    line_number: event.lineno,
    column_number: event.colno,
    stack_trace: event.error ? event.error.stack : null,
    user_agent: navigator.userAgent
  }, {
    category: 'system_event',
    immediate: true
  });
});

// API错误跟踪
function trackAPIError(url, status, response) {
  tracker.track('api_error', {
    endpoint: url,
    status_code: status,
    error_message: response.message || 'Unknown error',
    request_id: response.requestId || null,
    response_time: Date.now() - window.requestStartTime
  }, {
    category: 'system_event',
    immediate: true
  });
}

// 性能跟踪
function trackPerformance() {
  const navigation = performance.getEntriesByType('navigation')[0];
  const paint = performance.getEntriesByType('paint');
  
  tracker.track('page_performance', {
    dom_content_loaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
    load_complete: navigation.loadEventEnd - navigation.loadEventStart,
    first_paint: paint.find(p => p.name === 'first-paint')?.startTime || null,
    first_contentful_paint: paint.find(p => p.name === 'first-contentful-paint')?.startTime || null,
    dns_lookup: navigation.domainLookupEnd - navigation.domainLookupStart,
    tcp_connect: navigation.connectEnd - navigation.connectStart
  }, {
    category: 'system_event'
  });
}

// 页面加载完成后跟踪性能
window.addEventListener('load', () => {
  setTimeout(trackPerformance, 1000); // 等待1秒确保所有指标可用
});
```

## React集成示例

### React Hook

```javascript
import { useEffect, useRef } from 'react';

export function useEventTracker(options = {}) {
  const trackerRef = useRef(null);

  useEffect(() => {
    if (!trackerRef.current) {
      trackerRef.current = new EventTracker(options);
    }

    return () => {
      // 组件卸载时刷新事件
      if (trackerRef.current) {
        trackerRef.current.flush(true);
      }
    };
  }, []);

  const track = (eventType, data, options) => {
    if (trackerRef.current) {
      return trackerRef.current.track(eventType, data, options);
    }
  };

  const setUserId = (userId) => {
    if (trackerRef.current) {
      trackerRef.current.setUserId(userId);
    }
  };

  return { track, setUserId };
}
```

### React组件示例

```javascript
import React from 'react';
import { useEventTracker } from './hooks/useEventTracker';

function ProductPage({ product }) {
  const { track } = useEventTracker({
    baseUrl: process.env.REACT_APP_EVENT_SERVICE_URL
  });

  useEffect(() => {
    // 跟踪产品页面浏览
    track('product_viewed', {
      product_id: product.id,
      product_name: product.name,
      product_category: product.category,
      product_price: product.price
    }, {
      category: 'user_interaction'
    });
  }, [product.id]);

  const handleAddToCart = () => {
    track('add_to_cart', {
      product_id: product.id,
      quantity: 1,
      price: product.price
    }, {
      category: 'business_action',
      immediate: true
    });
    
    // 执行实际的添加到购物车逻辑
    addToCart(product);
  };

  return (
    <div>
      <h1>{product.name}</h1>
      <p>${product.price}</p>
      <button onClick={handleAddToCart}>
        Add to Cart
      </button>
    </div>
  );
}
```

## TypeScript类型定义

```typescript
interface EventData {
  [key: string]: any;
}

interface EventMetadata {
  [key: string]: string;
}

interface EventOptions {
  category?: 'user_interaction' | 'business_action' | 'system_event';
  immediate?: boolean;
  metadata?: EventMetadata;
}

interface TrackerOptions {
  baseUrl?: string;
  userId?: string | null;
  sessionId?: string;
  batchSize?: number;
  batchTimeout?: number;
}

class EventTracker {
  constructor(options?: TrackerOptions);
  track(eventType: string, data?: EventData, options?: EventOptions): Promise<any>;
  setUserId(userId: string): void;
  renewSession(): void;
  flush(sync?: boolean): Promise<any>;
}
```

## 最佳实践

### 1. 事件命名规范

```javascript
// 好的事件命名
tracker.track('product_viewed');
tracker.track('add_to_cart');
tracker.track('checkout_completed');

// 避免的命名
tracker.track('click'); // 太泛泛
tracker.track('ProductViewed'); // 不要使用驼峰命名
```

### 2. 数据隐私

```javascript
// 敏感数据处理
function trackLogin(userData) {
  tracker.track('user_logged_in', {
    // 不要发送密码、邮箱等敏感信息
    user_id: userData.id,
    account_type: userData.type,
    login_method: userData.method,
    // email: userData.email // ❌ 不要发送
  });
}
```

### 3. 性能优化

```javascript
// 使用批量发送减少网络请求
const tracker = new EventTracker({
  batchSize: 20,        // 适当的批量大小
  batchTimeout: 10000   // 10秒超时
});

// 重要事件立即发送
tracker.track('purchase_completed', data, { immediate: true });

// 普通事件批量发送
tracker.track('button_click', data); // 默认批量
```

### 4. 错误处理

```javascript
// 优雅降级
try {
  await tracker.track('important_event', data, { immediate: true });
} catch (error) {
  // 不应影响用户体验
  console.warn('Event tracking failed:', error);
}
```

这个前端集成指南基于我们成功测试的Event Service API，提供了完整的JavaScript SDK和实际使用示例。