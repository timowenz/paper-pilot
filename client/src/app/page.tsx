"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Upload,
  FileText,
  Download,
  RotateCcw,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/** When unset, requests go to `/api/...` and Next.js rewrites to the backend (see `next.config.ts`). */
const ANALYZE_PDF_URL = (() => {
  const base = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";
  return base ? `${base}/analyze-pdf` : "/api/analyze-pdf";
})();

type State = "idle" | "analyzing" | "done" | "error";

const STEPS = [
  "Parsing document",
  "Checking grammar & spelling",
  "Analyzing coherence with AI",
  "Annotating PDF",
];

function LoadingAnimation({ fileName }: { fileName: string }) {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setActiveStep((s) => (s + 1) % STEPS.length);
    }, 3000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="flex flex-col items-center gap-6 py-6">
      <div className="relative flex size-20 items-center justify-center">
        <svg
          className="absolute inset-2 size-[calc(100%-16px)] animate-spin"
          style={{ animationDuration: "1.5s" }}
          viewBox="0 0 64 64"
          fill="none"
        >
          <circle
            cx="32"
            cy="32"
            r="29"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeDasharray="50 132"
            className="text-primary/40"
          />
        </svg>
        <FileText className="size-7 text-primary" />
      </div>

      <div className="text-center">
        <p className="font-medium">{fileName}</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Analyzing your document
        </p>
      </div>

      <div className="flex w-full flex-col gap-1.5">
        {STEPS.map((step, i) => (
          <div
            key={step}
            className="flex items-center gap-2.5 rounded-md px-3 py-1.5 text-sm transition-colors duration-500"
            style={{
              color:
                i === activeStep
                  ? "var(--foreground)"
                  : "var(--muted-foreground)",
              backgroundColor:
                i === activeStep ? "var(--muted)" : "transparent",
            }}
          >
            <div
              className="size-1.5 shrink-0 rounded-full transition-colors duration-500"
              style={{
                backgroundColor:
                  i === activeStep
                    ? "var(--primary)"
                    : "var(--muted-foreground)",
                opacity: i === activeStep ? 1 : 0.35,
              }}
            />
            {step}
            {i === activeStep && (
              <span className="inline-flex w-4">
                <span className="animate-pulse">...</span>
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  const [mounted, setMounted] = useState(false);
  const [state, setState] = useState<State>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [resultName, setResultName] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => setMounted(true), []);

  const reset = useCallback(() => {
    if (resultUrl) URL.revokeObjectURL(resultUrl);
    setFile(null);
    setResultUrl(null);
    setResultName("");
    setErrorMsg("");
    setState("idle");
  }, [resultUrl]);

  const handleFile = (f: File | undefined) => {
    if (!f || f.type !== "application/pdf") return;
    setFile(f);
  };

  const analyze = async () => {
    if (!file) return;
    setState("analyzing");
    setErrorMsg("");

    try {
      const form = new FormData();
      form.append("file", file);

      const res = await fetch(ANALYZE_PDF_URL, {
        method: "POST",
        body: form,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Server error ${res.status}`);
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const baseName = file.name.replace(/\.pdf$/i, "");
      setResultUrl(url);
      setResultName(`${baseName}_annotated.pdf`);
      setState("done");
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "An unknown error occurred");
      setState("error");
    }
  };

  const download = () => {
    if (!resultUrl) return;
    const a = document.createElement("a");
    a.href = resultUrl;
    a.download = resultName;
    a.click();
  };

  if (!mounted) return null;

  return (
    <main className="flex flex-1 items-center justify-center p-6">
      <Card className="w-full max-w-md">
        <CardHeader>
          <div className="flex items-center gap-3">
            {/* Same mark as public/icon.svg (favicon) */}
            <img
              src="/icon.svg"
              alt=""
              width={32}
              height={32}
              className="size-8 shrink-0"
            />
            <CardTitle className="text-xl">Paper Pilot</CardTitle>
          </div>
          <CardDescription>
            Upload a PDF to check it for grammar, style, and coherence.
          </CardDescription>
        </CardHeader>

        <CardContent className="flex flex-col gap-4">
          {(state === "idle" || state === "error") && (
            <>
              <input
                ref={inputRef}
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={(e) => handleFile(e.target.files?.[0])}
              />

              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  handleFile(e.dataTransfer.files[0]);
                }}
                className="flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-muted-foreground/25 px-6 py-10 text-muted-foreground transition-colors hover:border-muted-foreground/50 hover:bg-muted/50"
              >
                {file ? (
                  <>
                    <FileText className="size-8" />
                    <span className="text-sm font-medium text-foreground">
                      {file.name}
                    </span>
                    <span className="text-xs">
                      {(file.size / 1024 / 1024).toFixed(1)} MB
                    </span>
                  </>
                ) : (
                  <>
                    <Upload className="size-8" />
                    <span className="text-sm">
                      Drop a PDF here or click to browse
                    </span>
                  </>
                )}
              </button>

              {state === "error" && (
                <p className="text-sm text-destructive">{errorMsg}</p>
              )}

              <Button
                size="lg"
                disabled={!file}
                onClick={analyze}
                className="w-full"
              >
                Start Analysis
              </Button>
            </>
          )}

          {state === "analyzing" && file && (
            <LoadingAnimation fileName={file.name} />
          )}

          {state === "done" && (
            <div className="flex flex-col items-center gap-4 py-8">
              <div className="flex size-12 items-center justify-center rounded-full bg-primary/10">
                <CheckCircle2 className="size-6 text-primary" />
              </div>
              <div className="text-center">
                <p className="font-medium">Analysis complete</p>
                <p className="text-sm text-muted-foreground">
                  Your annotated PDF is ready for download.
                </p>
              </div>
              <div className="flex w-full flex-col gap-2">
                <Button size="lg" onClick={download} className="w-full">
                  <Download className="size-4" />
                  Download PDF
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  onClick={reset}
                  className="w-full"
                >
                  <RotateCcw className="size-4" />
                  New Analysis
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
