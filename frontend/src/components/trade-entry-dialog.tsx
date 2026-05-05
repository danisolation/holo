"use client";

import { useState, useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ChevronsUpDown, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover";
import {
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "@/components/ui/command";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  useCreateTrade,
  useTickers,
  useDailyPicks,
  useProfile,
} from "@/lib/hooks";
import { ApiError } from "@/lib/api";
import type { TradeCreate, TradeResponse, Ticker } from "@/lib/api";
import { formatVND } from "@/lib/format";
import { Badge } from "@/components/ui/badge";

const tradeSchema = z.object({
  ticker_symbol: z.string().min(1, "Chọn mã chứng khoán"),
  side: z.enum(["BUY", "SELL"]),
  price: z.number().positive("Giá phải lớn hơn 0"),
  quantity: z
    .number()
    .positive("Số lượng phải lớn hơn 0")
    .refine((v) => v % 100 === 0, "Số lượng phải là bội số của 100"),
  trade_date: z.string().refine(
    (v) => {
      const d = new Date(v);
      const today = new Date();
      today.setHours(23, 59, 59, 999);
      return d <= today;
    },
    "Ngày giao dịch không được trong tương lai",
  ),
  user_notes: z.string().max(500).optional(),
  daily_pick_id: z.number().nullable().optional(),
  broker_fee_override: z.number().min(0).optional(),
  sell_tax_override: z.number().min(0).optional(),
});

type TradeForm = z.infer<typeof tradeSchema>;

export interface TradePrefill {
  ticker_symbol: string;
  ticker_name: string;
  price: number;
  quantity: number;
  daily_pick_id: number;
  stop_loss: number | null;
  take_profit_1: number | null;
}

interface TradeEntryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  prefill?: TradePrefill;
  onTradeCreated?: (trade: TradeResponse) => void;
}

export function TradeEntryDialog({
  open,
  onOpenChange,
  prefill,
  onTradeCreated,
}: TradeEntryDialogProps) {
  const [tickerOpen, setTickerOpen] = useState(false);
  const [selectedTicker, setSelectedTicker] = useState<Ticker | null>(null);
  const [feeOverrideEnabled, setFeeOverrideEnabled] = useState(false);
  const [apiError, setApiError] = useState("");
  const [pickLinkChecked, setPickLinkChecked] = useState(false);

  const mutation = useCreateTrade();
  const { data: tickers } = useTickers(undefined, undefined, 500);
  const { data: dailyPicksData } = useDailyPicks();
  const { data: profile } = useProfile();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<TradeForm>({
    resolver: zodResolver(tradeSchema),
    defaultValues: {
      side: "BUY",
      trade_date: new Date().toISOString().split("T")[0],
      daily_pick_id: null,
    },
  });

  const watchedPrice = watch("price");
  const watchedQuantity = watch("quantity");
  const watchedSide = watch("side");
  const watchedTickerSymbol = watch("ticker_symbol");

  // Fee auto-calculation
  const brokerFeePct = profile?.broker_fee_pct ?? 0.15;
  const brokerFee =
    watchedPrice && watchedQuantity
      ? Math.round((watchedPrice * watchedQuantity * brokerFeePct) / 100)
      : 0;
  const sellTax =
    watchedSide === "SELL" && watchedPrice && watchedQuantity
      ? Math.round(watchedPrice * watchedQuantity * 0.001)
      : 0;
  const totalFee = brokerFee + sellTax;

  // Pick link auto-suggestion
  const matchingPick = useMemo(() => {
    if (!watchedTickerSymbol || !dailyPicksData) return null;
    const allPicks = [
      ...(dailyPicksData.picks ?? []),
      ...(dailyPicksData.almost_selected ?? []),
    ];
    return (
      allPicks.find((p) => p.ticker_symbol === watchedTickerSymbol) ?? null
    );
  }, [watchedTickerSymbol, dailyPicksData]);

  // Auto-check pick link when match found
  useEffect(() => {
    if (matchingPick) {
      setPickLinkChecked(true);
      setValue("daily_pick_id", matchingPick.id);
    } else {
      setPickLinkChecked(false);
      setValue("daily_pick_id", null);
    }
  }, [matchingPick, setValue]);

  // Reset form on dialog close, or prefill on open
  useEffect(() => {
    if (!open) {
      reset({
        side: "BUY",
        trade_date: new Date().toISOString().split("T")[0],
        daily_pick_id: null,
      });
      setSelectedTicker(null);
      setFeeOverrideEnabled(false);
      setPickLinkChecked(false);
      setApiError("");
    } else if (prefill) {
      // Pre-fill from AI pick data
      reset({
        side: "BUY",
        ticker_symbol: prefill.ticker_symbol,
        price: prefill.price,
        quantity: prefill.quantity,
        trade_date: new Date().toISOString().split("T")[0],
        daily_pick_id: prefill.daily_pick_id,
      });
      setSelectedTicker({
        symbol: prefill.ticker_symbol,
        name: prefill.ticker_name,
      } as Ticker);
      setPickLinkChecked(true);
      setApiError("");
    }
  }, [open, prefill, reset]);

  async function onSubmit(data: TradeForm) {
    setApiError("");
    try {
      const payload: TradeCreate = {
        ticker_symbol: data.ticker_symbol,
        side: data.side,
        price: data.price,
        quantity: data.quantity,
        trade_date: data.trade_date,
        user_notes: data.user_notes || undefined,
        daily_pick_id: data.daily_pick_id ?? undefined,
      };
      if (feeOverrideEnabled) {
        payload.broker_fee_override = data.broker_fee_override;
        payload.sell_tax_override = data.sell_tax_override;
      }
      const result = await mutation.mutateAsync(payload);
      reset();
      setSelectedTicker(null);
      onOpenChange(false);
      onTradeCreated?.(result);
    } catch (err) {
      if (err instanceof ApiError) {
        setApiError(err.message);
      } else {
        setApiError("Không thể lưu lệnh. Vui lòng thử lại.");
      }
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{prefill ? "Ghi nhận giao dịch từ gợi ý" : "Ghi lệnh giao dịch"}</DialogTitle>
          <DialogDescription>
            Nhập thông tin lệnh mua hoặc bán thực tế.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="space-y-4">
            {/* Ticker autocomplete */}
            {prefill ? (
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">
                  Mã chứng khoán
                </label>
                <div className="flex items-center gap-2 rounded-md border border-input bg-muted/50 px-3 py-2">
                  <span className="font-mono font-bold text-sm">{prefill.ticker_symbol}</span>
                  <span className="text-sm text-muted-foreground">{prefill.ticker_name}</span>
                  <Badge variant="secondary" className="ml-auto text-xs">Từ gợi ý AI</Badge>
                </div>
              </div>
            ) : (
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">
                  Mã chứng khoán <span className="text-destructive">*</span>
                </label>
                <Popover open={tickerOpen} onOpenChange={setTickerOpen}>
                  <PopoverTrigger
                    render={
                      <Button
                        variant="outline"
                        type="button"
                        className="w-full justify-between font-normal"
                      />
                    }
                  >
                    {selectedTicker ? (
                      <span>
                        <span className="font-mono font-bold">
                          {selectedTicker.symbol}
                        </span>{" "}
                        <span className="text-muted-foreground">
                          {selectedTicker.name}
                        </span>
                      </span>
                    ) : (
                      <span className="text-muted-foreground">
                        Tìm mã CK...
                      </span>
                    )}
                    <ChevronsUpDown className="size-4 text-muted-foreground" />
                  </PopoverTrigger>
                  <PopoverContent className="w-[--anchor-width] p-0">
                    <Command shouldFilter={true}>
                      <CommandInput placeholder="Tìm mã CK..." />
                      <CommandList>
                        <CommandEmpty>Không tìm thấy mã nào.</CommandEmpty>
                        <CommandGroup>
                          {tickers?.map((ticker) => (
                            <CommandItem
                              key={ticker.symbol}
                              value={`${ticker.symbol} ${ticker.name}`}
                              onSelect={() => {
                                setValue("ticker_symbol", ticker.symbol, {
                                  shouldValidate: true,
                                });
                                setSelectedTicker(ticker);
                                setTickerOpen(false);
                              }}
                              className="cursor-pointer"
                            >
                              <span className="font-mono font-bold text-sm w-16">
                                {ticker.symbol}
                              </span>
                              <span className="text-muted-foreground text-sm truncate">
                                {ticker.name}
                              </span>
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
                {errors.ticker_symbol && (
                  <p className="text-xs text-destructive mt-1">
                    {errors.ticker_symbol.message}
                  </p>
                )}
              </div>
            )}

            {/* Side + Date row */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">
                  Loại lệnh <span className="text-destructive">*</span>
                </label>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    className={
                      watchedSide === "BUY"
                        ? "flex-1 text-[#26a69a] bg-[#26a69a]/10 border-[#26a69a]/30"
                        : "flex-1"
                    }
                    onClick={() => setValue("side", "BUY")}
                  >
                    MUA
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    className={
                      watchedSide === "SELL"
                        ? "flex-1 text-[#ef5350] bg-[#ef5350]/10 border-[#ef5350]/30"
                        : "flex-1"
                    }
                    onClick={() => setValue("side", "SELL")}
                  >
                    BÁN
                  </Button>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">
                  Ngày giao dịch <span className="text-destructive">*</span>
                </label>
                <Input type="date" {...register("trade_date")} />
                {errors.trade_date && (
                  <p className="text-xs text-destructive mt-1">
                    {errors.trade_date.message}
                  </p>
                )}
              </div>
            </div>

            {/* Price + Quantity row */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">
                  Giá (VND) <span className="text-destructive">*</span>
                </label>
                <Input
                  type="text"
                  inputMode="numeric"
                  placeholder="0"
                  onChange={(e) => {
                    const parsed = parseFloat(
                      e.target.value.replace(/[^0-9.]/g, ""),
                    );
                    setValue("price", isNaN(parsed) ? 0 : parsed, {
                      shouldValidate: true,
                    });
                  }}
                />
                {errors.price && (
                  <p className="text-xs text-destructive mt-1">
                    {errors.price.message}
                  </p>
                )}
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">
                  Số lượng (cổ) <span className="text-destructive">*</span>
                </label>
                <Input
                  type="text"
                  inputMode="numeric"
                  placeholder="0"
                  onChange={(e) => {
                    const parsed = parseInt(
                      e.target.value.replace(/[^0-9]/g, ""),
                      10,
                    );
                    setValue("quantity", isNaN(parsed) ? 0 : parsed, {
                      shouldValidate: true,
                    });
                  }}
                />
                {errors.quantity && (
                  <p className="text-xs text-destructive mt-1">
                    {errors.quantity.message}
                  </p>
                )}
              </div>
            </div>

            {/* Fee section */}
            <div className="border-t pt-4">
              <p className="text-xs font-medium text-muted-foreground mb-2">
                Phí giao dịch
              </p>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    Phí môi giới (tự tính)
                  </span>
                  <span className="font-mono text-sm text-muted-foreground">
                    {formatVND(brokerFee)} VND
                  </span>
                </div>
                {watchedSide === "SELL" && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      Thuế bán (0.1%)
                    </span>
                    <span className="font-mono text-sm text-muted-foreground">
                      {formatVND(sellTax)} VND
                    </span>
                  </div>
                )}
                <div className="flex justify-between font-medium">
                  <span>Tổng phí</span>
                  <span className="font-mono text-sm">
                    {formatVND(totalFee)} VND
                  </span>
                </div>
              </div>

              {/* Fee override checkbox */}
              <label className="flex items-center gap-2 mt-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={feeOverrideEnabled}
                  onChange={(e) => setFeeOverrideEnabled(e.target.checked)}
                  className="rounded border-input"
                />
                <span className="text-xs text-muted-foreground">
                  Tự nhập phí (ghi đè tính tự động)
                </span>
              </label>

              {feeOverrideEnabled && (
                <div className="grid grid-cols-2 gap-4 mt-2">
                  <div className="space-y-1">
                    <label className="text-xs text-muted-foreground">
                      Phí môi giới
                    </label>
                    <Input
                      type="text"
                      inputMode="numeric"
                      placeholder="0"
                      onChange={(e) => {
                        const parsed = parseFloat(
                          e.target.value.replace(/[^0-9.]/g, ""),
                        );
                        setValue(
                          "broker_fee_override",
                          isNaN(parsed) ? 0 : parsed,
                        );
                      }}
                    />
                  </div>
                  {watchedSide === "SELL" && (
                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground">
                        Thuế bán
                      </label>
                      <Input
                        type="text"
                        inputMode="numeric"
                        placeholder="0"
                        onChange={(e) => {
                          const parsed = parseFloat(
                            e.target.value.replace(/[^0-9.]/g, ""),
                          );
                          setValue(
                            "sell_tax_override",
                            isNaN(parsed) ? 0 : parsed,
                          );
                        }}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Pick link (conditional) */}
            {matchingPick && (
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={pickLinkChecked}
                  onChange={(e) => {
                    setPickLinkChecked(e.target.checked);
                    setValue(
                      "daily_pick_id",
                      e.target.checked ? matchingPick.id : null,
                    );
                  }}
                  className="rounded border-input"
                />
                <span className="text-xs text-muted-foreground">
                  Theo gợi ý AI — {matchingPick.ticker_symbol} #
                  {matchingPick.rank} ({matchingPick.pick_date})
                </span>
              </label>
            )}

            {/* Notes */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">
                Ghi chú (tùy chọn)
              </label>
              <Textarea
                placeholder="Lý do, chiến lược, ghi chú..."
                {...register("user_notes")}
              />
            </div>

            {/* API error */}
            {apiError && (
              <p className="text-sm text-destructive">{apiError}</p>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending && (
                <Loader2 className="size-4 animate-spin mr-2" />
              )}
              Lưu lệnh
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
