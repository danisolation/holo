"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useSectorPerformance } from "@/lib/hooks";
import type { ScreenerParams } from "@/lib/api";

interface ScreenerFiltersProps {
  params: ScreenerParams;
  onChange: (params: ScreenerParams) => void;
}

export function ScreenerFilters({ params, onChange }: ScreenerFiltersProps) {
  const { data: sectors } = useSectorPerformance();

  const [sector, setSector] = useState(params.sector ?? "");
  const [industry, setIndustry] = useState(params.industry ?? "");
  const [minVolume, setMinVolume] = useState(params.min_volume?.toString() ?? "");
  const [minChange, setMinChange] = useState(params.min_change?.toString() ?? "");
  const [maxChange, setMaxChange] = useState(params.max_change?.toString() ?? "");
  const [minPe, setMinPe] = useState(params.min_pe?.toString() ?? "");
  const [maxPe, setMaxPe] = useState(params.max_pe?.toString() ?? "");

  function handleFilter() {
    onChange({
      ...params,
      sector: sector || undefined,
      industry: industry || undefined,
      min_volume: minVolume ? Number(minVolume) : undefined,
      min_change: minChange ? Number(minChange) : undefined,
      max_change: maxChange ? Number(maxChange) : undefined,
      min_pe: minPe ? Number(minPe) : undefined,
      max_pe: maxPe ? Number(maxPe) : undefined,
      offset: 0,
    });
  }

  function handleClear() {
    setSector("");
    setIndustry("");
    setMinVolume("");
    setMinChange("");
    setMaxChange("");
    setMinPe("");
    setMaxPe("");
    onChange({ limit: params.limit, offset: 0 });
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <select
          value={sector}
          onChange={(e) => setSector(e.target.value)}
          className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          <option value="">Tất cả ngành</option>
          {sectors?.map((s) => (
            <option key={s.sector} value={s.sector}>
              {s.sector}
            </option>
          ))}
        </select>

        <Input
          placeholder="Ngành con (industry)"
          value={industry}
          onChange={(e) => setIndustry(e.target.value)}
        />

        <Input
          type="number"
          placeholder="KL tối thiểu"
          value={minVolume}
          onChange={(e) => setMinVolume(e.target.value)}
        />

        <Input
          type="number"
          placeholder="% thay đổi tối thiểu"
          value={minChange}
          onChange={(e) => setMinChange(e.target.value)}
        />

        <Input
          type="number"
          placeholder="% thay đổi tối đa"
          value={maxChange}
          onChange={(e) => setMaxChange(e.target.value)}
        />

        <Input
          type="number"
          placeholder="P/E tối thiểu"
          value={minPe}
          onChange={(e) => setMinPe(e.target.value)}
        />

        <Input
          type="number"
          placeholder="P/E tối đa"
          value={maxPe}
          onChange={(e) => setMaxPe(e.target.value)}
        />
      </div>

      <div className="flex gap-2">
        <Button size="sm" onClick={handleFilter}>
          Lọc
        </Button>
        <Button size="sm" variant="outline" onClick={handleClear}>
          Xóa bộ lọc
        </Button>
      </div>
    </div>
  );
}
