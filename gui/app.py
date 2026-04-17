from __future__ import annotations

import os
import queue
import sys
import threading
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models import PipelineOptions
from src.progress import ProgressCallback
from src.service import TranscriptService


class QueueProgressCallback(ProgressCallback):
    def __init__(self, event_queue: queue.Queue) -> None:
        self.event_queue = event_queue

    def on_info(self, message: str) -> None:
        self.event_queue.put(("log", message))

    def on_batch_start(self, total_files: int) -> None:
        self.event_queue.put(("batch_start", total_files))

    def on_file_start(self, index: int, total: int, file_path: Path) -> None:
        self.event_queue.put(("file_start", index, total, str(file_path)))

    def on_file_done(self, index: int, total: int, file_path: Path, output_path: Path) -> None:
        self.event_queue.put(("file_done", index, total, str(file_path), str(output_path)))

    def on_error(self, index: int, total: int, file_path: Path, error: str) -> None:
        self.event_queue.put(("file_error", index, total, str(file_path), error))

    def on_complete(self, total: int, success: int, failed: int) -> None:
        self.event_queue.put(("complete", total, success, failed))


class DesktopApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Whisper Transcription Desktop")
        self.geometry("1080x760")
        self.minsize(980, 680)

        self.event_queue: queue.Queue = queue.Queue()
        self.worker: threading.Thread | None = None

        self.mode_var = tk.StringVar(value="single")
        self.input_file_var = tk.StringVar(value="")
        self.input_dir_var = tk.StringVar(value=str((PROJECT_ROOT / "input").resolve()))
        self.output_dir_var = tk.StringVar(value=str((PROJECT_ROOT / "output").resolve()))
        self.output_name_var = tk.StringVar(value="")

        self.include_timestamps_var = tk.BooleanVar(value=False)
        self.include_speakers_var = tk.BooleanVar(value=False)
        self.recursive_var = tk.BooleanVar(value=False)

        self.model_var = tk.StringVar(value="large-v3")
        self.device_var = tk.StringVar(value="cuda")
        self.precision_var = tk.StringVar(value="fp32")
        self.language_var = tk.StringVar(value="")
        self.pause_threshold_var = tk.StringVar(value="1.2")
        self.max_speakers_var = tk.StringVar(value="2")
        self.ffmpeg_bin_var = tk.StringVar(value="ffmpeg")
        self.conflict_strategy_var = tk.StringVar(value="timestamp")

        self.status_var = tk.StringVar(value="Ready")

        self._build_ui()
        self._switch_mode()
        self.after(120, self._poll_events)

    def _build_ui(self) -> None:
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        mode_frame = ttk.LabelFrame(container, text="Input Mode", padding=10)
        mode_frame.pack(fill="x")
        ttk.Radiobutton(
            mode_frame,
            text="Single File",
            variable=self.mode_var,
            value="single",
            command=self._switch_mode,
        ).grid(row=0, column=0, sticky="w", padx=(0, 18))
        ttk.Radiobutton(
            mode_frame,
            text="Batch Folder",
            variable=self.mode_var,
            value="batch",
            command=self._switch_mode,
        ).grid(row=0, column=1, sticky="w")

        io_frame = ttk.LabelFrame(container, text="Input and Output", padding=10)
        io_frame.pack(fill="x", pady=(10, 0))

        ttk.Label(io_frame, text="Input File:").grid(row=0, column=0, sticky="w")
        self.input_file_entry = ttk.Entry(io_frame, textvariable=self.input_file_var, width=90)
        self.input_file_entry.grid(row=0, column=1, sticky="ew", padx=8)
        self.input_file_button = ttk.Button(io_frame, text="Browse", command=self._pick_input_file)
        self.input_file_button.grid(row=0, column=2, sticky="ew")

        ttk.Label(io_frame, text="Input Folder:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.input_dir_entry = ttk.Entry(io_frame, textvariable=self.input_dir_var, width=90)
        self.input_dir_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=(8, 0))
        self.input_dir_button = ttk.Button(io_frame, text="Browse", command=self._pick_input_dir)
        self.input_dir_button.grid(row=1, column=2, sticky="ew", pady=(8, 0))

        ttk.Label(io_frame, text="Output Folder:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(io_frame, textvariable=self.output_dir_var, width=90).grid(
            row=2,
            column=1,
            sticky="ew",
            padx=8,
            pady=(8, 0),
        )
        ttk.Button(io_frame, text="Browse", command=self._pick_output_dir).grid(
            row=2,
            column=2,
            sticky="ew",
            pady=(8, 0),
        )

        ttk.Label(io_frame, text="Output Name (single):").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(io_frame, textvariable=self.output_name_var, width=90).grid(
            row=3,
            column=1,
            sticky="ew",
            padx=8,
            pady=(8, 0),
        )

        io_frame.columnconfigure(1, weight=1)

        option_frame = ttk.LabelFrame(container, text="Output Options", padding=10)
        option_frame.pack(fill="x", pady=(10, 0))

        ttk.Checkbutton(
            option_frame,
            text="Include timestamps",
            variable=self.include_timestamps_var,
        ).grid(row=0, column=0, sticky="w", padx=(0, 16))
        ttk.Checkbutton(
            option_frame,
            text="Include speaker labels",
            variable=self.include_speakers_var,
        ).grid(row=0, column=1, sticky="w", padx=(0, 16))
        ttk.Checkbutton(
            option_frame,
            text="Recursive batch scan",
            variable=self.recursive_var,
        ).grid(row=0, column=2, sticky="w")

        advanced_frame = ttk.LabelFrame(container, text="Advanced", padding=10)
        advanced_frame.pack(fill="x", pady=(10, 0))

        ttk.Label(advanced_frame, text="Model").grid(row=0, column=0, sticky="w")
        ttk.Entry(advanced_frame, textvariable=self.model_var, width=14).grid(row=0, column=1, sticky="w", padx=(6, 14))

        ttk.Label(advanced_frame, text="Device").grid(row=0, column=2, sticky="w")
        ttk.Combobox(
            advanced_frame,
            textvariable=self.device_var,
            values=["cuda", "cpu"],
            state="readonly",
            width=10,
        ).grid(row=0, column=3, sticky="w", padx=(6, 14))

        ttk.Label(advanced_frame, text="Precision").grid(row=0, column=4, sticky="w")
        ttk.Combobox(
            advanced_frame,
            textvariable=self.precision_var,
            values=["fp32", "fp16"],
            state="readonly",
            width=10,
        ).grid(row=0, column=5, sticky="w", padx=(6, 14))

        ttk.Label(advanced_frame, text="Language").grid(row=0, column=6, sticky="w")
        ttk.Entry(advanced_frame, textvariable=self.language_var, width=10).grid(row=0, column=7, sticky="w", padx=(6, 14))

        ttk.Label(advanced_frame, text="Pause Threshold").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(advanced_frame, textvariable=self.pause_threshold_var, width=14).grid(
            row=1,
            column=1,
            sticky="w",
            padx=(6, 14),
            pady=(8, 0),
        )

        ttk.Label(advanced_frame, text="Max Speakers").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(advanced_frame, textvariable=self.max_speakers_var, width=10).grid(
            row=1,
            column=3,
            sticky="w",
            padx=(6, 14),
            pady=(8, 0),
        )

        ttk.Label(advanced_frame, text="FFmpeg Bin").grid(row=1, column=4, sticky="w", pady=(8, 0))
        ttk.Entry(advanced_frame, textvariable=self.ffmpeg_bin_var, width=28).grid(
            row=1,
            column=5,
            sticky="w",
            padx=(6, 14),
            pady=(8, 0),
            columnspan=2,
        )

        ttk.Label(advanced_frame, text="Conflict").grid(row=1, column=7, sticky="w", pady=(8, 0))
        ttk.Combobox(
            advanced_frame,
            textvariable=self.conflict_strategy_var,
            values=["timestamp", "sequence", "overwrite"],
            state="readonly",
            width=10,
        ).grid(row=1, column=8, sticky="w", padx=(6, 0), pady=(8, 0))

        action_frame = ttk.Frame(container)
        action_frame.pack(fill="x", pady=(10, 0))
        self.start_button = ttk.Button(action_frame, text="Start Transcription", command=self._start_transcription)
        self.start_button.pack(side="left")
        ttk.Button(action_frame, text="Open Output Folder", command=self._open_output_folder).pack(side="left", padx=(8, 0))

        status_frame = ttk.Frame(container)
        status_frame.pack(fill="x", pady=(10, 0))
        self.progress_bar = ttk.Progressbar(status_frame, mode="determinate")
        self.progress_bar.pack(fill="x")
        ttk.Label(status_frame, textvariable=self.status_var).pack(anchor="w", pady=(6, 0))

        log_frame = ttk.LabelFrame(container, text="Runtime Log", padding=8)
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        self.log_view = ScrolledText(log_frame, wrap="word", height=18)
        self.log_view.pack(fill="both", expand=True)
        self.log_view.configure(state="disabled")

    def _switch_mode(self) -> None:
        single_mode = self.mode_var.get() == "single"
        file_state = "normal" if single_mode else "disabled"
        dir_state = "disabled" if single_mode else "normal"

        self.input_file_entry.configure(state=file_state)
        self.input_file_button.configure(state=file_state)
        self.input_dir_entry.configure(state=dir_state)
        self.input_dir_button.configure(state=dir_state)

    def _append_log(self, message: str) -> None:
        self.log_view.configure(state="normal")
        self.log_view.insert("end", f"{message}\n")
        self.log_view.see("end")
        self.log_view.configure(state="disabled")

    def _pick_input_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select media file",
            filetypes=[
                ("Media files", "*.mp3 *.wav *.m4a *.flac *.aac *.ogg *.wma *.mp4 *.mkv *.mov *.avi *.webm *.flv *.wmv"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            self.input_file_var.set(selected)

    def _pick_input_dir(self) -> None:
        selected = filedialog.askdirectory(title="Select input folder")
        if selected:
            self.input_dir_var.set(selected)

    def _pick_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="Select output folder")
        if selected:
            self.output_dir_var.set(selected)

    def _open_output_folder(self) -> None:
        out_dir = Path(self.output_dir_var.get()).expanduser().resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(out_dir))
        except Exception as exc:
            messagebox.showerror("Open folder failed", str(exc))

    def _collect_options(self) -> PipelineOptions:
        language = self.language_var.get().strip() or None
        return PipelineOptions(
            model_name=self.model_var.get().strip() or "large-v3",
            device=self.device_var.get().strip() or "cuda",
            precision=self.precision_var.get().strip() or "fp32",
            language=language,
            include_timestamps=self.include_timestamps_var.get(),
            include_speakers=self.include_speakers_var.get(),
            pause_threshold_sec=float(self.pause_threshold_var.get().strip()),
            max_speakers=max(1, int(self.max_speakers_var.get().strip())),
            ffmpeg_bin=self.ffmpeg_bin_var.get().strip() or "ffmpeg",
            keep_temp_files=False,
            output_conflict_strategy=self.conflict_strategy_var.get().strip() or "timestamp",
        )

    def _start_transcription(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        mode = self.mode_var.get()
        output_dir = self.output_dir_var.get().strip()
        if not output_dir:
            messagebox.showwarning("Missing output", "Please select an output folder.")
            return

        if mode == "single":
            input_file = self.input_file_var.get().strip()
            if not input_file:
                messagebox.showwarning("Missing input", "Please select an input file.")
                return
        else:
            input_dir = self.input_dir_var.get().strip()
            if not input_dir:
                messagebox.showwarning("Missing input", "Please select an input folder.")
                return

        try:
            options = self._collect_options()
            options.validate()
        except Exception as exc:
            messagebox.showerror("Invalid options", str(exc))
            return

        self.start_button.configure(state="disabled")
        self.progress_bar.configure(mode="determinate", maximum=1, value=0)
        self.status_var.set("Running...")
        self._append_log("=== New run started ===")

        payload = {
            "mode": mode,
            "output_dir": output_dir,
            "output_name": self.output_name_var.get().strip() or None,
            "input_file": self.input_file_var.get().strip(),
            "input_dir": self.input_dir_var.get().strip(),
            "recursive": self.recursive_var.get(),
            "options": options,
        }
        self.worker = threading.Thread(target=self._run_worker, args=(payload,), daemon=True)
        self.worker.start()

    def _run_worker(self, payload: dict) -> None:
        callback = QueueProgressCallback(self.event_queue)
        try:
            service = TranscriptService(
                options=payload["options"],
                temp_dir=PROJECT_ROOT / "temp",
                models_dir=PROJECT_ROOT / "models",
            )

            if payload["mode"] == "single":
                result = service.transcribe_file(
                    input_file=payload["input_file"],
                    output_dir=payload["output_dir"],
                    output_name=payload["output_name"],
                    callback=callback,
                )
                self.event_queue.put(("single_done", str(result.output_file)))
            else:
                summary = service.transcribe_directory(
                    input_dir=payload["input_dir"],
                    output_dir=payload["output_dir"],
                    recursive=payload["recursive"],
                    callback=callback,
                )
                self.event_queue.put(
                    (
                        "batch_done",
                        summary.total_files,
                        summary.success_files,
                        summary.failed_files,
                    )
                )
                for path in summary.outputs:
                    self.event_queue.put(("log", f"Output: {path}"))
                for error in summary.errors:
                    self.event_queue.put(("log", f"Error: {error}"))
        except Exception as exc:
            self.event_queue.put(("fatal", str(exc), traceback.format_exc()))
        finally:
            self.event_queue.put(("worker_finished",))

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.event_queue.get_nowait()
                kind = event[0]

                if kind == "log":
                    self._append_log(event[1])
                elif kind == "batch_start":
                    total = max(1, int(event[1]))
                    self.progress_bar.configure(mode="determinate", maximum=total, value=0)
                    self.status_var.set(f"Batch started. Files: {total}")
                elif kind == "file_start":
                    _, index, total, file_path = event
                    if total > 1:
                        self.progress_bar.configure(mode="determinate", maximum=total)
                        self.progress_bar["value"] = max(0, index - 1)
                    else:
                        self.progress_bar.configure(mode="indeterminate")
                        self.progress_bar.start(12)
                    self.status_var.set(f"Processing {index}/{total}: {Path(file_path).name}")
                    self._append_log(f"Processing {index}/{total}: {file_path}")
                elif kind == "file_done":
                    _, index, total, _, output_path = event
                    if total > 1:
                        self.progress_bar["value"] = index
                    self._append_log(f"Done: {output_path}")
                elif kind == "file_error":
                    _, index, total, file_path, error = event
                    self._append_log(f"Failed {index}/{total}: {file_path}")
                    self._append_log(f"Reason: {error}")
                elif kind == "complete":
                    _, total, success, failed = event
                    self.status_var.set(f"Complete. total={total}, success={success}, failed={failed}")
                elif kind == "single_done":
                    output_file = event[1]
                    self._append_log(f"Output file: {output_file}")
                    self.status_var.set(f"Single file complete: {output_file}")
                    messagebox.showinfo("Completed", f"Transcript created:\n{output_file}")
                elif kind == "batch_done":
                    _, total, success, failed = event
                    messagebox.showinfo(
                        "Batch completed",
                        f"Total: {total}\nSuccess: {success}\nFailed: {failed}",
                    )
                elif kind == "fatal":
                    _, error, tb = event
                    self._append_log(f"Fatal error: {error}")
                    self._append_log(tb)
                    messagebox.showerror("Run failed", error)
                elif kind == "worker_finished":
                    if self.progress_bar["mode"] == "indeterminate":
                        self.progress_bar.stop()
                    self.start_button.configure(state="normal")
        except queue.Empty:
            pass
        finally:
            self.after(120, self._poll_events)


def main() -> None:
    app = DesktopApp()
    app.mainloop()


if __name__ == "__main__":
    main()
