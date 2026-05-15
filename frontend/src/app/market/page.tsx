"use client";

import Link from "next/link";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { SectorTab } from "@/components/market/sector-tab";
import { BreadthTab } from "@/components/market/breadth-tab";
import { FlowTab } from "@/components/market/flow-tab";

export default function MarketPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Thị trường</h2>
        <p className="text-sm text-muted-foreground">
          Phân tích ngành &amp; sức khỏe thị trường HOSE
        </p>
      </div>

      <div className="flex gap-2">
        <Link href="/market/screener">
          <Button variant="outline" size="sm">Bộ lọc cổ phiếu</Button>
        </Link>
      </div>

      <Tabs defaultValue={0}>
        <div className="w-full overflow-x-auto">
          <TabsList>
            <TabsTrigger value={0} className="flex-shrink-0">
              Sector
            </TabsTrigger>
            <TabsTrigger value={1} className="flex-shrink-0">
              Breadth
            </TabsTrigger>
            <TabsTrigger value={2} className="flex-shrink-0">
              Dòng tiền
            </TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value={0} className="pt-4">
          <SectorTab />
        </TabsContent>
        <TabsContent value={1} className="pt-4">
          <BreadthTab />
        </TabsContent>
        <TabsContent value={2} className="pt-4">
          <FlowTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
