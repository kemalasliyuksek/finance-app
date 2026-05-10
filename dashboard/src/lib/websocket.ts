type MessageHandler = (data: WebSocketMessage) => void;

export interface WebSocketMessage {
  type: "candle" | "signal" | "order" | "sentiment" | "config" | "screener" | "unknown";
  channel: string;
  data: Record<string, unknown>;
}

export class TradingWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private token: string;
  private handlers: Set<MessageHandler> = new Set();
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private shouldReconnect = true;

  constructor(url: string, token: string) {
    this.url = url;
    this.token = token;
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket(`${this.url}?token=${this.token}`);

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      if (event.data === "pong") return;
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        this.handlers.forEach((handler) => handler(message));
      } catch {
        // ignore parse errors
      }
    };

    this.ws.onclose = () => {
      this.stopHeartbeat();
      if (this.shouldReconnect) {
        setTimeout(() => this.connect(), this.reconnectDelay);
        this.reconnectDelay = Math.min(
          this.reconnectDelay * 2,
          this.maxReconnectDelay,
        );
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect() {
    this.shouldReconnect = false;
    this.stopHeartbeat();
    this.ws?.close();
    this.ws = null;
  }

  subscribe(handler: MessageHandler) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  updateToken(token: string) {
    this.token = token;
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.disconnect();
      this.shouldReconnect = true;
      this.connect();
    }
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send("ping");
      }
    }, 30000);
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }
}
