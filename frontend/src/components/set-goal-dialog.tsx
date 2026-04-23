"use client";

import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useSetGoal } from "@/lib/hooks";

interface SetGoalDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentTarget?: number;
}

function getCurrentMonthLabel(): string {
  const now = new Date();
  return `${now.getMonth() + 1}/${now.getFullYear()}`;
}

export function SetGoalDialog({
  open,
  onOpenChange,
  currentTarget,
}: SetGoalDialogProps) {
  const [targetValue, setTargetValue] = useState<number | "">(
    currentTarget ?? "",
  );
  const [error, setError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const mutation = useSetGoal();

  // Reset form state when dialog opens
  useEffect(() => {
    if (open) {
      setTargetValue(currentTarget ?? "");
      setError(null);
      setServerError(null);
    }
  }, [open, currentTarget]);

  function validate(value: number | ""): string | null {
    if (value === "" || value <= 0) return "Mục tiêu tối thiểu 100,000 VND";
    if (value < 100_000) return "Mục tiêu tối thiểu 100,000 VND";
    if (value > 1_000_000_000) return "Mục tiêu tối đa 1,000,000,000 VND";
    return null;
  }

  async function handleSubmit() {
    const validationError = validate(targetValue);
    if (validationError) {
      setError(validationError);
      return;
    }

    setServerError(null);
    try {
      await mutation.mutateAsync(targetValue as number);
      onOpenChange(false);
    } catch {
      setServerError("Không thể lưu mục tiêu. Thử lại sau.");
    }
  }

  const hasError = error !== null || serverError !== null;
  const errorId = "goal-input-error";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Đặt mục tiêu lợi nhuận</DialogTitle>
          <DialogDescription>
            Mục tiêu lãi ròng cho tháng {getCurrentMonthLabel()}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          <label className="text-sm font-bold" htmlFor="goal-target-input">
            Số tiền mục tiêu (VND)
          </label>
          <Input
            id="goal-target-input"
            type="number"
            placeholder="5,000,000"
            className={`font-mono ${hasError ? "border-destructive" : ""}`}
            value={targetValue}
            onChange={(e) => {
              const val = e.target.value === "" ? "" : Number(e.target.value);
              setTargetValue(val);
              setError(null);
              setServerError(null);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSubmit();
            }}
            aria-describedby={hasError ? errorId : undefined}
          />
          {error && (
            <p id={errorId} className="text-xs text-destructive mt-1">
              {error}
            </p>
          )}
          {serverError && (
            <p id={errorId} className="text-xs text-destructive mt-1">
              {serverError}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={mutation.isPending}
          >
            Hủy
          </Button>
          <Button
            variant="default"
            onClick={handleSubmit}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? (
              <>
                <Loader2 className="size-4 animate-spin mr-1" />
                Đang lưu...
              </>
            ) : (
              "Lưu mục tiêu"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
