"use client";

import { useState } from "react";
import { ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "@/components/ui/command";

interface SectorComboboxProps {
  value: string | null;
  onChange: (sector: string | null) => void;
  sectors: string[];
}

export function SectorCombobox({ value, onChange, sectors }: SectorComboboxProps) {
  const [open, setOpen] = useState(false);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        render={<button type="button" />}
        className={cn(
          "flex items-center gap-1 rounded-md px-2 py-1 text-xs hover:bg-muted/50 transition-colors max-w-[160px] cursor-pointer",
          !value && "text-muted-foreground"
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <span className="truncate">{value || "Chọn ngành..."}</span>
        <ChevronsUpDown className="size-3 shrink-0 opacity-50" />
      </PopoverTrigger>
      <PopoverContent className="w-[220px] p-0" align="start">
        <Command>
          <CommandInput placeholder="Tìm ngành..." />
          <CommandList>
            <CommandEmpty>Không tìm thấy.</CommandEmpty>
            <CommandGroup>
              {sectors.map((sector) => (
                <CommandItem
                  key={sector}
                  value={sector}
                  data-checked={value === sector || undefined}
                  onSelect={() => {
                    onChange(sector === value ? null : sector);
                    setOpen(false);
                  }}
                >
                  {sector}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
