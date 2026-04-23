"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Settings, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useProfile, useUpdateProfile } from "@/lib/hooks";

const profileSchema = z.object({
  capital: z.number().positive("Vốn phải lớn hơn 0"),
  risk_level: z.number().min(1).max(5),
});

type ProfileForm = z.infer<typeof profileSchema>;

const RISK_LABELS: Record<number, string> = {
  1: "Rất thận trọng",
  2: "Thận trọng",
  3: "Cân bằng",
  4: "Tích cực",
  5: "Mạo hiểm",
};

const formatCapitalDisplay = (value: number): string => {
  return new Intl.NumberFormat("vi-VN").format(value);
};

const parseCapitalInput = (raw: string): number => {
  const cleaned = raw.replace(/[^0-9]/g, "");
  return parseInt(cleaned, 10) || 0;
};

export function ProfileSettingsCard() {
  const [open, setOpen] = useState(false);
  const { data: profile } = useProfile();
  const mutation = useUpdateProfile();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      capital: profile?.capital ?? 50_000_000,
      risk_level: profile?.risk_level ?? 3,
    },
  });

  // Sync form when profile loads
  useEffect(() => {
    if (profile) {
      reset({
        capital: profile.capital,
        risk_level: profile.risk_level,
      });
    }
  }, [profile, reset]);

  const riskLevel = watch("risk_level");
  const capitalValue = watch("capital");

  const [capitalDisplay, setCapitalDisplay] = useState(() =>
    formatCapitalDisplay(profile?.capital ?? 50_000_000),
  );

  // Keep display in sync with profile data
  useEffect(() => {
    if (profile) {
      setCapitalDisplay(formatCapitalDisplay(profile.capital));
    }
  }, [profile]);

  const onSubmit = (data: ProfileForm) => {
    mutation.mutate(data, {
      onSuccess: () => setOpen(false),
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={<Button variant="ghost" size="icon-sm" />}
      >
        <Settings className="size-4" />
        <span className="sr-only">Cài đặt hồ sơ</span>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Cài đặt hồ sơ</DialogTitle>
          <DialogDescription>
            Điều chỉnh vốn và mức rủi ro để nhận gợi ý phù hợp.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Capital input */}
          <div className="space-y-2">
            <label className="text-sm font-bold">Vốn đầu tư (VND)</label>
            <Input
              type="text"
              inputMode="numeric"
              value={capitalDisplay}
              onChange={(e) => {
                const raw = e.target.value;
                const num = parseCapitalInput(raw);
                setCapitalDisplay(raw.replace(/[^0-9,.]/g, "") || "");
                setValue("capital", num, { shouldValidate: true });
              }}
              onBlur={() => {
                // Reformat on blur
                setCapitalDisplay(formatCapitalDisplay(capitalValue));
              }}
            />
            {errors.capital && (
              <p className="text-sm text-destructive">
                {errors.capital.message}
              </p>
            )}
          </div>

          {/* Risk level selector */}
          <div className="space-y-2">
            <label className="text-sm font-bold">Mức rủi ro</label>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5].map((level) => (
                <Button
                  key={level}
                  type="button"
                  variant={riskLevel === level ? "default" : "outline"}
                  size="sm"
                  className="flex-1"
                  onClick={() =>
                    setValue("risk_level", level, { shouldValidate: true })
                  }
                >
                  {level}
                </Button>
              ))}
            </div>
            <p className="text-sm text-muted-foreground">
              {RISK_LABELS[riskLevel] ?? "Cân bằng"}
            </p>
          </div>

          {/* Error message */}
          {mutation.isError && (
            <p className="text-sm text-destructive">
              Không thể lưu. Vui lòng thử lại.
            </p>
          )}

          {/* Save button */}
          <Button
            type="submit"
            variant="default"
            className="w-full"
            disabled={mutation.isPending}
          >
            {mutation.isPending && (
              <Loader2 className="size-4 animate-spin mr-2" />
            )}
            Lưu cài đặt
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
