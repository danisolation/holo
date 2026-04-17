"use client";

import { useCallback, useRef, useState } from "react";
import { FileUp, FileText, X, CheckCircle, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useCSVDryRun, useCSVImport } from "@/lib/hooks";
import { CSVPreviewTable } from "@/components/csv-preview-table";
import type { CSVDryRunResponse } from "@/lib/api";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB

export default function CSVImportDialog() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [file, setFile] = useState<File | null>(null);
  const [fileSizeError, setFileSizeError] = useState<string | null>(null);
  const [dryRunResult, setDryRunResult] = useState<CSVDryRunResponse | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const dryRunMutation = useCSVDryRun();
  const importMutation = useCSVImport();

  const resetAll = useCallback(() => {
    setStep(1);
    setFile(null);
    setFileSizeError(null);
    setDryRunResult(null);
    setImportError(null);
    dryRunMutation.reset();
    importMutation.reset();
  }, [dryRunMutation, importMutation]);

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      resetAll();
    }
    setOpen(nextOpen);
  };

  const validateFile = (f: File): boolean => {
    setFileSizeError(null);
    if (f.size > MAX_FILE_SIZE) {
      setFileSizeError("File quá lớn. Giới hạn 5MB.");
      return false;
    }
    return true;
  };

  const handleFileSelect = (f: File) => {
    if (validateFile(f)) {
      setFile(f);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFileSelect(f);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFileSelect(f);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleContinue = () => {
    if (!file) return;
    dryRunMutation.mutate(file, {
      onSuccess: (result) => {
        setDryRunResult(result);
        setStep(2);
      },
    });
  };

  const handleConfirmImport = () => {
    if (!file) return;
    setImportError(null);
    importMutation.mutate(file, {
      onSuccess: () => {
        setStep(3);
      },
      onError: (err) => {
        setImportError(err.message);
      },
    });
  };

  const handleBack = () => {
    setStep(1);
    setDryRunResult(null);
    setImportError(null);
  };

  const removeFile = () => {
    setFile(null);
    setFileSizeError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger
        render={
          <Button variant="outline" size="sm">
            <Upload className="size-4 mr-1" />
            Nhập CSV
          </Button>
        }
      />
      <DialogContent className="sm:max-w-2xl">
        {/* Step 1: Upload */}
        {step === 1 && (
          <>
            <DialogHeader>
              <DialogTitle>Nhập giao dịch từ CSV</DialogTitle>
              <DialogDescription>
                Hỗ trợ file xuất từ VNDirect và SSI. Hệ thống sẽ tự nhận dạng định dạng.
              </DialogDescription>
            </DialogHeader>

            {/* Drop zone */}
            <div
              className={`border-2 border-dashed rounded-lg p-8 flex flex-col items-center justify-center gap-2 cursor-pointer transition-colors ${
                isDragOver
                  ? "border-primary bg-primary/10"
                  : "border-border hover:border-primary hover:bg-primary/5"
              }`}
              onClick={() => fileInputRef.current?.click()}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
            >
              <FileUp className="size-12 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                Kéo thả file CSV vào đây
              </span>
              <span className="text-xs text-muted-foreground">
                hoặc nhấn để chọn file
              </span>
              <span className="text-xs text-muted-foreground/60">
                Hỗ trợ: VNDirect, SSI
              </span>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleInputChange}
              />
            </div>

            {/* File size error */}
            {fileSizeError && (
              <p className="text-xs text-[#ef5350]">{fileSizeError}</p>
            )}

            {/* Selected file info */}
            {file && (
              <div className="flex items-center gap-2 text-sm">
                <FileText className="size-4 text-muted-foreground" />
                <span>{file.name}</span>
                <span className="text-muted-foreground">
                  ({formatFileSize(file.size)})
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile();
                  }}
                >
                  <X className="size-3" />
                </Button>
              </div>
            )}

            {/* Dry run error */}
            {dryRunMutation.isError && (
              <p className="text-xs text-[#ef5350]">
                {dryRunMutation.error?.message}
              </p>
            )}

            <DialogFooter>
              <Button
                disabled={!file || dryRunMutation.isPending}
                onClick={handleContinue}
              >
                {dryRunMutation.isPending ? "Đang phân tích..." : "Tiếp tục"}
              </Button>
            </DialogFooter>
          </>
        )}

        {/* Step 2: Preview */}
        {step === 2 && dryRunResult && (
          <>
            <DialogHeader>
              <DialogTitle>Xem trước giao dịch</DialogTitle>
              <DialogDescription>
                Kiểm tra {dryRunResult.rows.length} giao dịch trước khi nhập.{" "}
                {dryRunResult.total_errors} lỗi, {dryRunResult.total_warnings} cảnh báo.
              </DialogDescription>
            </DialogHeader>

            {/* Summary bar */}
            <div className="bg-muted rounded-lg p-3 flex flex-wrap items-center gap-4">
              <span className="text-sm text-[#26a69a]">
                ✓ {dryRunResult.total_valid} hợp lệ
              </span>
              <span className="text-sm text-[#f59e0b]">
                ⚠ {dryRunResult.total_warnings} cảnh báo
              </span>
              <span className="text-sm text-[#ef5350]">
                ✗ {dryRunResult.total_errors} lỗi
              </span>
              <span className="text-xs text-muted-foreground">
                Định dạng: {dryRunResult.format_detected}
              </span>
            </div>

            {/* Preview table */}
            {importMutation.isPending ? (
              <Skeleton className="h-[360px] w-full rounded-lg" />
            ) : (
              <CSVPreviewTable rows={dryRunResult.rows} />
            )}

            {/* Import error banner */}
            {importError && (
              <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-3">
                <p className="text-sm text-destructive">
                  Không thể nhập giao dịch. {importError}
                </p>
              </div>
            )}

            <DialogFooter>
              <Button variant="outline" onClick={handleBack}>
                Quay lại
              </Button>
              <Button
                disabled={dryRunResult.total_errors > 0 || importMutation.isPending}
                onClick={handleConfirmImport}
              >
                {importMutation.isPending
                  ? "Đang nhập..."
                  : `Xác nhận nhập ${dryRunResult.total_valid} giao dịch`}
              </Button>
            </DialogFooter>
          </>
        )}

        {/* Step 3: Result */}
        {step === 3 && importMutation.data && (
          <>
            <div className="flex flex-col items-center justify-center gap-3 p-8">
              <CheckCircle className="size-12 text-[#26a69a]" />
              <p className="text-lg font-semibold">
                Đã nhập {importMutation.data.trades_imported} giao dịch thành công
              </p>
              <p className="text-sm text-muted-foreground">
                FIFO đã được tính lại cho {importMutation.data.tickers_recalculated} mã cổ phiếu
              </p>
            </div>

            <DialogFooter>
              <Button onClick={() => handleOpenChange(false)}>
                Đóng
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
