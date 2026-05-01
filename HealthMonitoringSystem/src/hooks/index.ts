/**
 * hooks/index.ts
 * 统一导出所有Hooks
 */

export { useDynamicWebSocket, useModuleWebSocket } from './useDynamicWebSocket';
export type {
  ModuleType,
  ConnectionStatus,
  WebSocketMessage,
  UseDynamicWebSocketOptions,
  UseDynamicWebSocketReturn
} from './useDynamicWebSocket';