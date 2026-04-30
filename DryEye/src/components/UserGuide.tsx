import React from 'react';
import { Card } from './ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Alert, AlertDescription } from './ui/alert';
import { Wifi, Settings, Monitor, HelpCircle, Shield, Zap, Battery } from 'lucide-react';

export function UserGuide() {
  return (
    <Card className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <HelpCircle className="h-6 w-6 text-blue-600" />
        <h2>使用说明</h2>
      </div>
      
      <Tabs defaultValue="setup" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="setup">系统设置</TabsTrigger>
          <TabsTrigger value="operation">操作指南</TabsTrigger>
          <TabsTrigger value="alerts">警报说明</TabsTrigger>
          <TabsTrigger value="maintenance">维护保养</TabsTrigger>
        </TabsList>
        
        <TabsContent value="setup" className="space-y-4">
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <Wifi className="h-5 w-5 text-blue-600 mt-1" />
              <div>
                <h4 className="mb-2">传感器安装</h4>
                <ul className="space-y-1 text-sm text-muted-foreground list-disc list-inside">
                  <li>将柔性传感器轻轻贴在上眼皮处</li>
                  <li>确保传感器与皮肤良好接触</li>
                  <li>避免传感器过紧或过松</li>
                  <li>检查传感器无线连接状态</li>
                </ul>
              </div>
            </div>
            
            <div className="flex items-start gap-3">
              <Battery className="h-5 w-5 text-blue-600 mt-1" />
              <div>
                <h4 className="mb-2">电源管理</h4>
                <ul className="space-y-1 text-sm text-muted-foreground list-disc list-inside">
                  <li>使用前确保传感器电量充足</li>
                  <li>建议电量低于20%时及时充电</li>
                  <li>长期不使用时请关闭传感器</li>
                  <li>充电时使用专用充电器</li>
                </ul>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Settings className="h-5 w-5 text-blue-600 mt-1" />
              <div>
                <h4 className="mb-2">系统配置</h4>
                <ul className="space-y-1 text-sm text-muted-foreground list-disc list-inside">
                  <li>根据个人特征进行传感器校准</li>
                  <li>设置合适的干眼风险检测阈值</li>
                  <li>配置警报方式和强度</li>
                  <li>检查数据同步和存储设置</li>
                </ul>
              </div>
            </div>
          </div>
        </TabsContent>
        
        <TabsContent value="operation" className="space-y-4">
          <div className="space-y-4">
            <Alert>
              <Monitor className="h-4 w-4" />
              <AlertDescription>
                启动系统前，请确保传感器已正确佩戴并连接成功。
              </AlertDescription>
            </Alert>
            
            <div className="space-y-3">
              <h4>操作步骤</h4>
              <ol className="space-y-2 text-sm list-decimal list-inside">
                <li>确认传感器连接状态正常</li>
                <li>进行传感器校准（首次使用必须）</li>
                <li>点击"开始监控"按钮启动系统</li>
                <li>观察实时数据面板，确保各项指标正常</li>
                <li>关注眨眼频率和眼部稳定性变化</li>
                <li>注意警报提示，及时响应干眼风险警告</li>
                <li>监测结束后点击"停止监控"</li>
                <li>查看历史健康数据和趋势报告</li>
              </ol>
            </div>
          </div>
        </TabsContent>
        
        <TabsContent value="alerts" className="space-y-4">
          <div className="space-y-4">
            <h4>警报级别说明</h4>
            
            <div className="space-y-3">
              <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <div>
                  <div className="text-sm">正常状态</div>
                  <div className="text-xs text-muted-foreground">眼部健康评分 &gt; 70%，状态良好</div>
                </div>
              </div>
              
              <div className="flex items-center gap-3 p-3 bg-yellow-50 rounded-lg">
                <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                <div>
                  <div className="text-sm">干眼预警</div>
                  <div className="text-xs text-muted-foreground">眼部健康评分 30-70%，建议适当休息</div>
                </div>
              </div>
              
              <div className="flex items-center gap-3 p-3 bg-red-50 rounded-lg">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <div>
                  <div className="text-sm">干眼高风险</div>
                  <div className="text-xs text-muted-foreground">眼部健康评分 &lt; 30%，建议咨询专业意见</div>
                </div>
              </div>
            </div>
          </div>
        </TabsContent>
        
        <TabsContent value="maintenance" className="space-y-4">
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <Shield className="h-5 w-5 text-blue-600 mt-1" />
              <div>
                <h4 className="mb-2">日常维护</h4>
                <ul className="space-y-1 text-sm text-muted-foreground list-disc list-inside">
                  <li>定期清洁传感器表面</li>
                  <li>检查传感器充电状态</li>
                  <li>更新传感器固件版本</li>
                  <li>备份监测数据</li>
                </ul>
              </div>
            </div>
            
            <div className="flex items-start gap-3">
              <Zap className="h-5 w-5 text-blue-600 mt-1" />
              <div>
                <h4 className="mb-2">故障排除</h4>
                <ul className="space-y-1 text-sm text-muted-foreground list-disc list-inside">
                  <li>检测不准确：重新进行传感器校准</li>
                  <li>传感器无法连接：检查电源和蓝牙</li>
                  <li>误报频繁：调整检测灵敏度</li>
                  <li>信号质量差：调整传感器位置</li>
                </ul>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </Card>
  );
}